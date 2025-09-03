from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.database import get_db
from app.config import get_settings, Settings
from app.utils.logger import setup_logger
from app.models.student import Student
from app.schemas.sms import BulkSMSRequest, FeeNotificationRequest, SMSFilter
from app.services.sms_service import SMSService
from app.services.phone_validator import PhoneValidatorService

router = APIRouter()
logger = setup_logger()

def get_sms_service(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db)
) -> SMSService:
    return SMSService(settings, db)

@router.post("/fee-notification", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def send_fee_notification_sms(
    request: FeeNotificationRequest,
    db: AsyncSession = Depends(get_db),
    sms_service: SMSService = Depends(get_sms_service)
):
    """
    Sends fee status notification SMS to specific students' parents.
    """
    if not request.student_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No student IDs provided for fee notification."
        )

    result = await db.execute(select(Student).filter(Student.id.in_(request.student_ids)))
    students = result.scalars().all()
    if not students:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No students found for the provided IDs."
        )

    results = []
    try:
        for student in students:
            try:
                # Prepare template variables, overriding with any provided in the request
                template_vars = {
                    "student_name": student.name,
                    "fee_status": student.fee_status,
                    **(request.template_vars or {})
                }
                message = sms_service.render_message_template(
                    template_name="fee_notification",
                    **template_vars
                )
            except ValueError as e:
                logger.error(f"Failed to render message template for student {student.id}: {e}")
                results.append({
                    "student_id": str(student.id),
                    "status": "failed",
                    "detail": f"Template rendering error: {e}"
                })
                continue

            # Send to parent1_phone
            result1 = await sms_service.send_sms(
                to=student.parent1_phone,
                message=message,
                student_id=str(student.id)
            )
            results.append({
                "student_id": str(student.id),
                "parent1_phone": student.parent1_phone,
                "status": result1["status"],
                "detail": result1.get("detail")
            })

            # Send to parent2_phone if available
            if student.parent2_phone:
                result2 = await sms_service.send_sms(
                    to=student.parent2_phone,
                    message=message,
                    student_id=str(student.id)
                )
                results.append({
                    "student_id": str(student.id),
                    "parent2_phone": student.parent2_phone,
                    "status": result2["status"],
                    "detail": result2.get("detail")
                })
        
        await db.commit()

        successful_sends = sum(1 for r in results if r.get("status") == "success")
        if successful_sends == 0 and students: # Only raise if there were students but no successful sends
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send any SMS notifications."
            )
        elif not students: # If no students were found, the initial check should have caught it, but as a safeguard
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No students found for the provided IDs."
            )

        return {"message": "Fee notification SMS sending initiated.", "results": results}
    except Exception as e:
        logger.error(f"Transaction failed for fee notification SMS: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during SMS notification: {e}"
        )

from app.models.sms_log import SMSLog
from app.schemas.sms_log import SMSLogResponse

@router.post("/bulk", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def send_bulk_sms_to_filtered_groups(
    request: BulkSMSRequest,
    db: AsyncSession = Depends(get_db),
    sms_service: SMSService = Depends(get_sms_service)
):
    """
    Sends bulk SMS messages to filtered groups of students' parents.
    """
    query = select(Student)

    if request.filters:
        if request.filters.grades:
            query = query.where(Student.grade.in_(request.filters.grades))
        if request.filters.fee_status:
            query = query.where(Student.fee_status == request.filters.fee_status)

    result = await db.execute(query)
    students = result.scalars().all()

    if not students:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No students found matching the provided filters."
        )

    recipients = set()
    for student in students:
        recipients.add(student.parent1_phone)
        if not request.use_primary_contact and student.parent2_phone:
            recipients.add(student.parent2_phone)

    if not recipients:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No valid recipients found for the filtered students."
        )

    bulk_results = await sms_service.send_bulk_sms(list(recipients), request.message)

    successful_sends = sum(1 for r in bulk_results if r.get("status") == "success")
    if successful_sends == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send any bulk SMS messages."
        )

    return {"message": "Bulk SMS sending initiated.", "results": bulk_results}

@router.get("/history", response_model=List[SMSLogResponse], status_code=status.HTTP_200_OK)
async def get_sms_history(
    db: AsyncSession = Depends(get_db),
    student_id: Optional[UUID] = None,
    status: Optional[str] = None,
    template_name: Optional[str] = None,
    skip: int = 0,
    limit: int = 10
):
    """
    Retrieves SMS history logs.

    This endpoint retrieves the history of SMS messages sent. It supports filtering by student ID, status, and template name. Pagination is supported via the skip and limit parameters.

    - **student_id**: Optional UUID to filter logs by student ID.
    - **status**: Optional string to filter logs by status (e.g., 'success', 'failed').
    - **template_name**: Optional string to filter logs by template name.
    - **skip**: Integer for pagination, number of logs to skip.
    - **limit**: Integer for pagination, maximum number of logs to return.

    - **returns**: List of SMSLogResponse objects representing the SMS history logs.
    """
    query = select(SMSLog)

    if student_id:
        query = query.where(SMSLog.student_id == student_id)
    if status:
        query = query.where(SMSLog.status == status)
    if template_name:
        query = query.where(SMSLog.template_name == template_name)

    result = await db.execute(query.offset(skip).limit(limit))
    sms_logs = result.scalars().all()

    return sms_logs
