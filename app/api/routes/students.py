from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Dict, Any
from uuid import UUID
import re
import csv
from io import StringIO

from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate, StudentInDB
from app.database import get_db
from app.services.phone_validator import PhoneValidatorService
from app.services.student_importer import StudentImporterService # Import the new service
from app.utils.logger import setup_logger

def _validate_class_letter(class_letter: str):
    """
    Validates if the class_letter is a valid single uppercase letter A-Z.
    """
    if not class_letter or not isinstance(class_letter, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="class_letter is required and must be a string"
        )
    
    if not re.match(r'^[A-Z]$', class_letter.upper()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="class_letter must be a single letter from A to Z"
        )
    
    return class_letter.upper()

def _validate_grade(grade: str):
    """
    Validates if the grade is one of the valid school grades.
    """
    valid_grades = ['Grade R', 'Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5', 'Grade 6', 'Grade 7']
    
    if grade not in valid_grades:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid grade: {grade}. Must be one of {valid_grades}"
        )

router = APIRouter()
logger = setup_logger()

@router.post("/import-csv", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def import_students_csv(
    file: UploadFile = File(..., description="CSV file containing student data"),
    db: AsyncSession = Depends(get_db)
):
    """
    Import student data from a CSV file.

    The CSV file should have the following columns:
    name,grade,class_letter,parent1_phone,parent2_phone,fee_status

    Args:
        file: The uploaded CSV file.
        db: Database session.

    Returns:
        A dictionary summarizing the import results (successful and failed imports).
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only CSV files are allowed."
        )

    try:
        # Read the CSV file content
        csv_content = await file.read()
        csv_content_str = csv_content.decode('utf-8')

        # Pass content to the importer service
        import_summary = await StudentImporterService.import_students_from_csv(db, csv_content_str)
        
        if import_summary["failed_imports"]:
            status_code = status.HTTP_207_MULTI_STATUS # Some records failed
        else:
            status_code = status.HTTP_200_OK

        logger.info(f"CSV import process finished for file '{file.filename}'. Summary: {import_summary}")
        return import_summary

    except HTTPException:
        raise # Re-raise HTTPExceptions
    except Exception as e:
        logger.error(f"Error processing CSV file '{file.filename}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV file: {e}"
        )

@router.post("/", response_model=StudentInDB, status_code=status.HTTP_201_CREATED)
async def create_student(student: StudentCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new student record.

    Args:
        student: Student data to create
        db: Database session

    Returns:
        Created student record
    """
    try:
        # Validate phone numbers
        try:
            student.parent1_phone = PhoneValidatorService._clean_and_validate_phone(student.parent1_phone)
        except ValueError as e:
            logger.error(f"Invalid parent1 phone number: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parent1 phone number: {str(e)}"
            )

        try:
            if student.parent2_phone:  # Only validate if provided
                student.parent2_phone = PhoneValidatorService._clean_and_validate_phone(student.parent2_phone)
        except ValueError as e:
            logger.error(f"Invalid parent2 phone number: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parent2 phone number: {str(e)}"
            )

        # Validate grade and class_letter
        _validate_grade(student.grade)
        student.class_letter = _validate_class_letter(student.class_letter)

        # Create student
        db_student = Student(**student.dict())
        db.add(db_student)
        await db.commit()
        await db.refresh(db_student)

        logger.info(f"Created student: {db_student.id}, Grade: {db_student.grade}, Class: {db_student.class_letter}")
        return db_student

    except SQLAlchemyError as e:
        logger.error(f"Database error creating student: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.get("/", response_model=List[StudentInDB])
async def read_students(
    grade: Optional[str] = Query(None, description="Filter by grade, e.g., 'Grade 1'"),
    class_letter: Optional[str] = Query(None, description="Filter by class letter, e.g., 'A'"),
    fee_status: Optional[str] = Query(None, description="Filter by fee status ('paid' or 'unpaid')"),
    sort_by: Optional[str] = Query(None, description="Sort by field (e.g., 'name', 'grade', 'class_letter')"),
    sort_order: Optional[str] = Query("asc", description="Sort order ('asc' or 'desc')"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a list of students with optional grade, class, and fee status filtering.

    Args:
        grade: Optional grade filter
        class_letter: Optional class letter filter
        fee_status: Optional fee status filter
        sort_by: Optional field to sort by
        sort_order: Sort order (asc or desc)
        db: Database session

    Returns:
        List of student records
    """
    try:
        query = select(Student)
        
        # Apply filters
        if grade:
            query = query.where(Student.grade == grade)
        if class_letter:
            query = query.where(Student.class_letter == class_letter.upper())
        if fee_status:
            if fee_status not in ["paid", "unpaid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="fee_status must be either 'paid' or 'unpaid'"
                )
            query = query.where(Student.fee_status == fee_status)

        # Apply sorting
        if sort_by:
            if sort_by not in ["name", "grade", "class_letter", "fee_status", "created_at", "updated_at"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid sort_by field. Must be 'name', 'grade', 'class_letter', 'fee_status', 'created_at', or 'updated_at'."
                )
            
            sort_column = getattr(Student, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            # Default sort order: grade, then class, then name
            query = query.order_by(Student.grade.asc(), Student.class_letter.asc(), Student.name.asc())

        result = await db.execute(query)
        students = result.scalars().all()

        # Build log message
        log_parts = []
        if grade:
            log_parts.append(f"grade {grade}")
        if class_letter:
            log_parts.append(f"class {class_letter}")
        if fee_status:
            log_parts.append(f"fee status {fee_status}")
        
        log_message = f"Fetched {len(students)} students"
        if log_parts:
            log_message += f" for {', '.join(log_parts)}"
        
        logger.info(log_message)
        return students

    except SQLAlchemyError as e:
        logger.error(f"Database error fetching students: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.get("/statistics", response_model=dict)
async def get_statistics(db: AsyncSession = Depends(get_db)):
    """
    Get summary statistics about students.

    Args:
        db: Database session

    Returns:
        Dictionary with statistics
    """
    try:
        # Get total students
        total_result = await db.execute(select(func.count(Student.id)))
        total_students = total_result.scalar()

        # Get fee status counts
        paid_result = await db.execute(
            select(func.count(Student.id)).where(Student.fee_status == "paid")
        )
        paid_students = paid_result.scalar()
        unpaid_students = total_students - paid_students

        # Get students by grade and class
        grade_class_result = await db.execute(
            select(Student.grade, Student.class_letter, func.count(Student.id))
            .group_by(Student.grade, Student.class_letter)
            .order_by(Student.grade, Student.class_letter)
        )
        students_by_grade_class = {}
        for grade, class_letter, count in grade_class_result:
            if grade not in students_by_grade_class:
                students_by_grade_class[grade] = {}
            students_by_grade_class[grade][class_letter] = count

        # Get fee status by grade and class
        grade_class_fee_result = await db.execute(
            select(
                Student.grade,
                Student.class_letter,
                Student.fee_status,
                func.count(Student.id)
            )
            .group_by(Student.grade, Student.class_letter, Student.fee_status)
            .order_by(Student.grade, Student.class_letter, Student.fee_status)
        )
        fee_status_by_grade_class = {}
        for grade, class_letter, fee_status, count in grade_class_fee_result:
            if grade not in fee_status_by_grade_class:
                fee_status_by_grade_class[grade] = {}
            if class_letter not in fee_status_by_grade_class[grade]:
                fee_status_by_grade_class[grade][class_letter] = {"paid": 0, "unpaid": 0}
            fee_status_by_grade_class[grade][class_letter][fee_status] = count

        stats = {
            "total_students": total_students,
            "paid_students": paid_students,
            "unpaid_students": unpaid_students,
            "students_by_grade_class": students_by_grade_class,
            "fee_status_by_grade_class": fee_status_by_grade_class,
        }

        logger.info("Generated student statistics including breakdown by grade and class")
        return stats

    except SQLAlchemyError as e:
        logger.error(f"Database error generating statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.get("/grades", response_model=List[str])
async def get_grades(db: AsyncSession = Depends(get_db)):
    """
    Get the list of available grades dynamically from existing students.

    Args:
        db: Database session

    Returns:
        List of unique grades, sorted
    """
    try:
        result = await db.execute(select(Student.grade).distinct().order_by(Student.grade))
        grades = result.scalars().all()
        logger.info(f"Fetched available grades: {grades}")
        return grades
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching grades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.get("/classes/{grade}", response_model=List[str])
async def get_classes_for_grade(grade: str, db: AsyncSession = Depends(get_db)):
    """
    Get the list of available classes for a specific grade dynamically from existing students.

    Args:
        grade: The grade to filter classes by, e.g., 'Grade 1'
        db: Database session

    Returns:
        List of unique class letters for the specified grade, sorted alphabetically
    """
    try:
        # Validate grade first
        _validate_grade(grade)
        
        result = await db.execute(
            select(Student.class_letter)
            .where(Student.grade == grade)
            .distinct()
            .order_by(Student.class_letter)
        )
        classes = result.scalars().all()
        logger.info(f"Fetched available classes for grade {grade}: {classes}")
        return classes
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching classes for grade {grade}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.get("/{student_id}", response_model=StudentInDB)
async def read_student(student_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get a specific student by ID.

    Args:
        student_id: Student UUID
        db: Database session

    Returns:
        Student record
    """
    try:
        result = await db.execute(select(Student).where(Student.id == student_id))
        student = result.scalar_one_or_none()

        if not student:
            logger.warning(f"Student not found: {student_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )

        logger.info(f"Fetched student: {student_id}")
        return student

    except SQLAlchemyError as e:
        logger.error(f"Database error fetching student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.put("/{student_id}", response_model=StudentInDB)
async def update_student(
    student_id: UUID,
    student_update: StudentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a student record.

    Args:
        student_id: Student UUID
        student_update: Updated student data
        db: Database session

    Returns:
        Updated student record
    """
    try:
        result = await db.execute(select(Student).where(Student.id == student_id))
        student = result.scalar_one_or_none()

        if not student:
            logger.warning(f"Student not found for update: {student_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )

        # Validate phone numbers if provided
        if student_update.parent1_phone is not None:
            try:
                student_update.parent1_phone = PhoneValidatorService._clean_and_validate_phone(student_update.parent1_phone)
            except ValueError as e:
                logger.error(f"Invalid parent1 phone number during update: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid parent1 phone number: {str(e)}"
                )
        
        if student_update.parent2_phone is not None:
            try:
                student_update.parent2_phone = PhoneValidatorService._clean_and_validate_phone(student_update.parent2_phone)
            except ValueError as e:
                logger.error(f"Invalid parent2 phone number during update: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid parent2 phone number: {str(e)}"
                )

        # Validate grade if being updated
        if student_update.grade is not None:
            _validate_grade(student_update.grade)
        
        # Validate class_letter if being updated
        if student_update.class_letter is not None:
            student_update.class_letter = _validate_class_letter(student_update.class_letter)

        # Update student fields
        for key, value in student_update.dict(exclude_unset=True).items():
            setattr(student, key, value)

        await db.commit()
        await db.refresh(student)

        logger.info(f"Updated student: {student_id}, Grade: {student.grade}, Class: {student.class_letter}")
        return student

    except SQLAlchemyError as e:
        logger.error(f"Database error updating student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(student_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a student record.

    Args:
        student_id: Student UUID
        db: Database session
    """
    try:
        result = await db.execute(select(Student).where(Student.id == student_id))
        student = result.scalar_one_or_none()

        if not student:
            logger.warning(f"Student not found for deletion: {student_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )

        await db.delete(student)
        await db.commit()

        logger.info(f"Deleted student: {student_id}, Grade: {student.grade}, Class: {student.class_letter}")

    except SQLAlchemyError as e:
        logger.error(f"Database error deleting student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.patch("/{student_id}/fee-status", response_model=StudentInDB)
async def update_fee_status(
    student_id: UUID,
    fee_status: str = Query(..., description="New fee status ('paid' or 'unpaid')"),
    db: AsyncSession = Depends(get_db)
):
    """
    Update only the fee status of a student.

    Args:
        student_id: Student UUID
        fee_status: New fee status ('paid' or 'unpaid')
        db: Database session

    Returns:
        Updated student record
    """
    try:
        result = await db.execute(select(Student).where(Student.id == student_id))
        student = result.scalar_one_or_none()

        if not student:
            logger.warning(f"Student not found for fee status update: {student_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )

        if fee_status not in ["paid", "unpaid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fee_status must be either 'paid' or 'unpaid'"
            )

        student.fee_status = fee_status
        await db.commit()
        await db.refresh(student)

        logger.info(f"Updated fee status for student {student_id}: {fee_status}")
        return student

    except SQLAlchemyError as e:
        logger.error(f"Database error updating fee status for student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )