from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base

class SMSLog(Base):
    __tablename__ = "sms_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=True)
    recipient_phone = Column(String(12), nullable=False)
    message_content = Column(Text, nullable=False)
    status = Column(String(20), nullable=False) # e.g., 'success', 'failed', 'pending'
    error_detail = Column(Text, nullable=True)
    api_message_id = Column(String(50), nullable=True) # To store WinSMS API message ID
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    is_bulk = Column(Boolean, default=False)
    template_name = Column(String(50), nullable=True)

    student = relationship("Student", back_populates="sms_logs")
