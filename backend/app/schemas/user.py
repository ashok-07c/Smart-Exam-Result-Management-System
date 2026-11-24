"""Student / faculty schemas."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import AccountStatus, EnrollmentStatus


class StudentOut(BaseModel):
    id: UUID
    user_id: UUID
    roll_number: str
    full_name: str
    email: EmailStr | None = None
    department: str | None = None
    branch: str | None = None
    department_id: UUID | None = None
    branch_id: UUID | None = None
    current_semester: int
    academic_year: str
    admission_year: str
    enrollment_status: EnrollmentStatus
    section: str | None = None

    model_config = {"from_attributes": True}


class StudentCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    roll_number: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=200)
    department_id: UUID | None = None
    branch_id: UUID | None = None
    current_semester: int = Field(default=1, ge=1, le=12)
    academic_year: str = Field(min_length=1, max_length=32)
    admission_year: str = Field(min_length=1, max_length=32)
    section: str | None = None
    must_change_password: bool = False


class StudentUpdate(BaseModel):
    """Administrative update; academic context is only editable by an admin."""

    full_name: str | None = None
    department_id: UUID | None = None
    branch_id: UUID | None = None
    current_semester: int | None = Field(default=None, ge=1, le=12)
    academic_year: str | None = None
    section: str | None = None
    enrollment_status: EnrollmentStatus | None = None


class StudentSelfUpdate(BaseModel):
    """Fields a student may change without weakening eligibility scoping."""

    full_name: str | None = None
    section: str | None = None


class FacultyOut(BaseModel):
    id: UUID
    user_id: UUID
    faculty_id: str
    full_name: str
    email: EmailStr | None = None
    department: str | None = None
    department_id: UUID | None = None
    designation: str
    account_status: AccountStatus

    model_config = {"from_attributes": True}


class FacultyCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    faculty_id: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=200)
    department_id: UUID | None = None
    designation: str = "Faculty"


class FacultyUpdate(BaseModel):
    full_name: str | None = None
    department_id: UUID | None = None
    designation: str | None = None
    account_status: AccountStatus | None = None
