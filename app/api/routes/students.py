from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from uuid import UUID

from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate, StudentInDB
from app.database import get_db
from app.services.phone_validator import PhoneValidatorService # Import the service class
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger()

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

        # Create student
        db_student = Student(**student.dict())
        db.add(db_student)
        await db.commit()
        await db.refresh(db_student)

        logger.info(f"Created student: {db_student.id}")
        return db_student

    except SQLAlchemyError as e:
        logger.error(f"Database error creating student: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.get("/", response_model=List[StudentInDB])
async def read_students(
    grade: Optional[str] = Query(None, description="Filter by grade"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a list of students with optional grade filtering.

    Args:
        grade: Optional grade filter
        db: Database session

    Returns:
        List of student records
    """
    try:
        query = select(Student)
        if grade:
            query = query.where(Student.grade == grade)

        result = await db.execute(query)
        students = result.scalars().all()

        logger.info(f"Fetched {len(students)} students" + (f" for grade {grade}" if grade else ""))
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
        # Get total studentsfunc
        total_result = await db.execute(select(func.count(Student.id)))
        total_students = total_result.scalar()

        # Get fee status counts
        paid_result = await db.execute(
            select(func.count(Student.id)).where(Student.fee_status == "paid")
        )
        paid_students = paid_result.scalar()

        unpaid_students = total_students - paid_students

        # Get students by grade
        grade_result = await db.execute(
            select(Student.grade, func.count(Student.id)).group_by(Student.grade)
        )
        students_by_grade = dict(grade_result.all())

        # Get fee status by grade
        grade_fee_result = await db.execute(
            select(
                Student.grade,
                Student.fee_status,
                func.count(Student.id)
            ).group_by(Student.grade, Student.fee_status)
        )
        fee_status_by_grade = {}
        for grade, fee_status, count in grade_fee_result:
            if grade not in fee_status_by_grade:
                fee_status_by_grade[grade] = {"paid": 0, "unpaid": 0}
            fee_status_by_grade[grade][fee_status] = count

        stats = {
            "total_students": total_students,
            "paid_students": paid_students,
            "unpaid_students": unpaid_students,
            "students_by_grade": students_by_grade,
            "fee_status_by_grade": fee_status_by_grade
        }

        logger.info("Generated student statistics")
        return stats

    except SQLAlchemyError as e:
        logger.error(f"Database error generating statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.get("/grades", response_model=List[str])
async def get_grades():
    """
    Get the list of available grades.

    Returns:
        List of grade strings
    """
    grades = [
        "Grade R", "Grade 1", "Grade 2", "Grade 3",
        "Grade 4", "Grade 5", "Grade 6", "Grade 7"
    ]
    logger.info("Fetched available grades")
    return grades

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

        # Update student
        for key, value in student_update.dict(exclude_unset=True).items():
            setattr(student, key, value)

        await db.commit()
        await db.refresh(student)

        logger.info(f"Updated student: {student_id}")
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

        logger.info(f"Deleted student: {student_id}")

    except SQLAlchemyError as e:
        logger.error(f"Database error deleting student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )

@router.patch("/{student_id}/fee-status", response_model=StudentInDB)
async def update_fee_status(
    student_id: UUID,
    fee_status: str,
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


