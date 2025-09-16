from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class SMSLogBase(BaseModel):
    student_id: Optional[UUID] = None
    recipient_phone: str = Field(..., min_length=10, max_length=12)
    message_content: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    error_detail: Optional[str] = None
    api_message_id: Optional[str] = None # To store WinSMS API message ID
    is_bulk: bool = False
    template_name: Optional[str] = None

class SMSLogCreate(SMSLogBase):
    pass

class SMSLogResponse(SMSLogBase):
    id: UUID
    sent_at: datetime

    class Config:
        from_attributes = True
