from sqlalchemy import Column, String, DateTime, UniqueConstraint, func, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.sms_log import SMSLog # Import SMSLog

class Student(Base):
    __tablename__ = "students"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    grade = Column(String(10), nullable=False)
    class_letter = Column(String(1), nullable=False, default='A')
    parent1_phone = Column(String(12), nullable=False)
    parent2_phone = Column(String(12), nullable=True)
    fee_status = Column(String(20), nullable=False, default="unpaid")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sms_logs = relationship("SMSLog", back_populates="student") # Add this line

    __table_args__ = (
        CheckConstraint(grade.in_(['Grade R', 'Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5', 'Grade 6', 'Grade 7']), name='check_grade'),
        CheckConstraint(fee_status.in_(['paid', 'unpaid']), name='check_fee_status'),
        CheckConstraint(class_letter.regexp_match('^[A-Z]$'), name='check_class_letter'),
        UniqueConstraint('name', 'grade', 'class_letter', name='uq_student_name_grade_class'),
    )
