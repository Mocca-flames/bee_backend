from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from uuid import UUID

class SMSFilter(BaseModel):
    grades: Optional[List[str]] = None
    fee_status: Optional[str] = None

class BulkSMSRequest(BaseModel):
    message: str = Field(..., min_length=1)
    filters: Optional[SMSFilter] = None
    use_primary_contact: bool = True

class FeeNotificationRequest(BaseModel):
    student_ids: List[UUID]
    template_name: str = Field(..., min_length=1)
    template_vars: Optional[Dict[str, str]] = None
