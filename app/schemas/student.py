from datetime import datetime # Import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID
# import re # No longer needed if using _clean_and_validate_phone

from app.services.phone_validator import PhoneValidatorService # Import the service class

class StudentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    grade: str
    parent1_phone: str
    parent2_phone: Optional[str] = None
    fee_status: str = "unpaid"

    @field_validator('grade')
    def validate_grade(cls, v):
        valid_grades = ['Grade R', 'Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5', 'Grade 6', 'Grade 7']
        if v not in valid_grades:
            raise ValueError(f'Grade must be one of: {", ".join(valid_grades)}')
        return v

    @field_validator('fee_status')
    def validate_fee_status(cls, v):
        if v not in ['paid', 'unpaid']:
            raise ValueError('fee_status must be either "paid" or "unpaid"')
        return v

    @field_validator('parent1_phone', 'parent2_phone', mode='before')
    def validate_phone(cls, v, info):
        if v is None:
            return v
        try:
            # Use the robust validation and cleaning function
            return PhoneValidatorService._clean_and_validate_phone(v)
        except ValueError as e:
            raise ValueError(f'{info.field_name} validation failed: {e}')

class StudentCreate(StudentBase):
    pass

class StudentUpdate(StudentBase):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    grade: Optional[str] = None
    parent1_phone: Optional[str] = None
    parent2_phone: Optional[str] = None
    fee_status: Optional[str] = None

class StudentInDB(StudentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
