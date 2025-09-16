import csv
from io import StringIO
from typing import List, Dict, Any
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import select

from app.schemas.csv_student import CSVStudent
from app.models.student import Student
from app.utils.logger import setup_logger

logger = setup_logger()

class StudentImporterService:
    @staticmethod
    async def import_students_from_csv(db: AsyncSession, csv_file_content: str) -> Dict[str, Any]:
        successful_imports = []
        failed_imports = []
        
        csv_reader = csv.DictReader(StringIO(csv_file_content))
        
        for i, row in enumerate(csv_reader):
            row_number = i + 2  # +1 for 0-based index, +1 for header row
            
            # Create a savepoint for this individual row
            savepoint = await db.begin_nested()
            
            try:
                # Clean up keys to match Pydantic schema
                cleaned_row = {k.strip().lower(): v.strip() for k, v in row.items()}
                
                csv_student_data = CSVStudent(**cleaned_row)

                # Check if student already exists
                existing_student_query = await db.execute(
                    select(Student).where(
                        Student.name == csv_student_data.name,
                        Student.grade == csv_student_data.grade,
                        Student.class_letter == csv_student_data.class_letter
                    )
                )
                existing_student = existing_student_query.scalar_one_or_none()

                if existing_student:
                    # Update existing student
                    existing_student.parent1_phone = csv_student_data.parent1_phone
                    existing_student.parent2_phone = csv_student_data.parent2_phone
                    existing_student.fee_status = csv_student_data.fee_status
                    await savepoint.commit()
                    successful_imports.append({
                        "row": row_number, 
                        "name": csv_student_data.name, 
                        "status": "updated"
                    })
                    logger.info(f"Successfully updated existing student from CSV: {csv_student_data.name}")
                else:
                    # Create a new Student model instance
                    db_student = Student(
                        name=csv_student_data.name,
                        grade=csv_student_data.grade,
                        class_letter=csv_student_data.class_letter,
                        parent1_phone=csv_student_data.parent1_phone,
                        parent2_phone=csv_student_data.parent2_phone,
                        fee_status=csv_student_data.fee_status
                    )
                    db.add(db_student)
                    await savepoint.commit()
                    successful_imports.append({
                        "row": row_number, 
                        "name": csv_student_data.name, 
                        "status": "created"
                    })
                    logger.info(f"Successfully created new student from CSV: {csv_student_data.name}")

            except ValidationError as e:
                await savepoint.rollback()
                failed_imports.append({
                    "row": row_number, 
                    "data": row, 
                    "errors": [{"field": err["loc"], "message": err["msg"]} for err in e.errors()]
                })
                logger.warning(f"Validation error for row {row_number} in CSV: {e.errors()}")
                
            except IntegrityError as e:
                await savepoint.rollback()
                # This shouldn't happen given our upsert logic, but just in case
                if "duplicate key value violates unique constraint" in str(e):
                    failed_imports.append({
                        "row": row_number, 
                        "data": row, 
                        "errors": f"Duplicate student: {csv_student_data.name if 'csv_student_data' in locals() else 'Unknown'}"
                    })
                    logger.warning(f"Duplicate key constraint violation for row {row_number}: {csv_student_data.name if 'csv_student_data' in locals() else 'Unknown'}")
                else:
                    failed_imports.append({
                        "row": row_number, 
                        "data": row, 
                        "errors": str(e)
                    })
                    logger.error(f"Integrity constraint violation for row {row_number}: {e}")
                    
            except SQLAlchemyError as e:
                await savepoint.rollback()
                failed_imports.append({
                    "row": row_number, 
                    "data": row, 
                    "errors": str(e)
                })
                logger.error(f"Database error for row {row_number} in CSV: {e}")
                
            except Exception as e:
                await savepoint.rollback()
                failed_imports.append({
                    "row": row_number, 
                    "data": row, 
                    "errors": str(e)
                })
                logger.error(f"Unexpected error for row {row_number} in CSV: {e}")

        # Commit all successful changes
        try:
            await db.commit()
            logger.info(f"CSV import complete. Successful: {len(successful_imports)}, Failed: {len(failed_imports)}")
        except SQLAlchemyError as e:
            await db.rollback()
            logger.critical(f"Final database commit failed for CSV import: {e}")
            # Mark all as failed due to commit failure
            all_failed = successful_imports + failed_imports
            failed_imports = []
            for item in all_failed:
                item["status"] = "failed_on_commit"
                item["errors"] = str(e)
                failed_imports.append(item)
            successful_imports = []

        return {
            "total_rows_processed": len(successful_imports) + len(failed_imports),
            "successful_imports": successful_imports,
            "failed_imports": failed_imports
        }