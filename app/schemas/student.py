from datetime import datetime # Import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID
# import re # No longer needed if using _clean_and_validate_phone

from app.services.phone_validator import PhoneValidatorService # Import the service class

class StudentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    grade: str
    class_letter: str = Field('A', min_length=1, max_length=1) # Default to 'A'
    parent1_phone: str
    parent2_phone: Optional[str] = None
    fee_status: str = "unpaid"


    @field_validator('fee_status')
    def validate_fee_status(cls, v):
        if v not in ['paid', 'unpaid']:
            raise ValueError('fee_status must be either "paid" or "unpaid"')
        return v

    @field_validator('grade')
    def validate_grade(cls, v):
        valid_grades = ['Grade R', 'Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5', 'Grade 6', 'Grade 7']
        if v not in valid_grades:
            raise ValueError(f'Grade must be one of: {", ".join(valid_grades)}')
        return v

    @field_validator('class_letter')
    def validate_class_letter(cls, v):
        if not (isinstance(v, str) and len(v) == 1 and 'A' <= v <= 'Z'):
            raise ValueError('Class letter must be a single uppercase letter (A-Z)')
        return v

    @field_validator('parent1_phone', 'parent2_phone', mode='before')
    def validate_phone(cls, v, info):
        if v is None or (isinstance(v, str) and v.lower() == 'null'):
            return None
        if not v:  # Handles empty strings after checking for None/ "null"
            return None
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
    class_letter: Optional[str] = Field(None, min_length=1, max_length=1)
    parent1_phone: Optional[str] = None
    parent2_phone: Optional[str] = None
    fee_status: Optional[str] = None

class StudentInDB(StudentBase):
    id: UUID
    class_letter: str # Ensure class_letter is included in the response model
    created_at: datetime
    updated_at: datetime

    @property
    def full_class(self) -> str:
        return f"{self.grade}{self.class_letter}"

    class Config:
        orm_mode = True
        # Allow properties to be included in the model's dictionary representation
        # and thus in the API response.
        # This might require Pydantic v2 or custom serialization for older versions.
        # For Pydantic v1, you might need to use `json_encoders` or `getter_dict`.
        # Assuming Pydantic v2 for simplicity with `@property`.
        # If using Pydantic v1, `orm_mode = True` usually handles properties if they are
        # directly on the SQLAlchemy model, but for a Pydantic property,
        # you might need to explicitly include it or use a custom `json_encoder`.
        # For FastAPI, `response_model` will typically pick up properties.
