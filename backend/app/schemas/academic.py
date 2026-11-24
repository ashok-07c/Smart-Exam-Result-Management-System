"""Academic structure and assignment schemas."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import SubjectType


class DepartmentOut(BaseModel):
    id: UUID
    department_name: str
    department_code: str

    model_config = {"from_attributes": True}


class BranchOut(BaseModel):
    id: UUID
    branch_name: str
    branch_code: str
    department_id: UUID | None = None

    model_config = {"from_attributes": True}


class RegulationOut(BaseModel):
    id: UUID
    regulation_name: str
    effective_year: str
    grade_rules: dict
    pass_rules: dict
    calculation_rules: dict

    model_config = {"from_attributes": True}


class AcademicYearCreate(BaseModel):
    academic_year_name: str = Field(pattern=r"^\d{4}-\d{2}$")
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("academic_year_name")
    @classmethod
    def year_not_before_2023(cls, value: str) -> str:
        start = int(value.split("-")[0])
        if start < 2023:
            raise ValueError("Academic year must start from 2023 or later")
        return value


class RegulationCreate(BaseModel):
    """Regulations no longer require JSON grade/pass rule configuration."""

    model_config = {"extra": "forbid"}

    regulation_name: str
    effective_year: str


class SemesterOut(BaseModel):
    id: UUID
    semester_number: int
    academic_year_id: UUID | None = None
    regulation_id: UUID | None = None

    model_config = {"from_attributes": True}


class CourseOut(BaseModel):
    id: UUID
    course_name: str
    course_code: str
    branch_id: UUID | None = None
    regulation_id: UUID | None = None
    duration_years: int

    model_config = {"from_attributes": True}


class CourseCreate(BaseModel):
    course_name: str
    course_code: str
    branch_id: UUID | None = None
    regulation_id: UUID | None = None
    duration_years: int = 4


class SubjectOut(BaseModel):
    id: UUID
    subject_code: str
    subject_name: str
    course_id: UUID | None = None
    semester_id: UUID | None = None
    credits: int
    internal_max_marks: int
    external_max_marks: int
    subject_type: SubjectType
    assessment_configuration: dict

    model_config = {"from_attributes": True}


class SubjectCreate(BaseModel):
    subject_code: str
    subject_name: str
    course_id: UUID | None = None
    semester_id: UUID | None = None
    credits: int = Field(ge=0, le=20)
    internal_max_marks: int = Field(default=30, ge=0)
    external_max_marks: int = Field(default=70, ge=0)
    subject_type: SubjectType = SubjectType.THEORY
    assessment_configuration: dict = Field(default_factory=dict)


class AssignmentOut(BaseModel):
    id: UUID
    faculty_id: UUID
    subject_id: UUID
    branch_id: UUID | None = None
    semester_id: UUID | None = None
    academic_year_id: UUID | None = None
    section: str | None = None
    assignment_status: str
    subject: SubjectOut | None = None
    faculty_name: str | None = None

    model_config = {"from_attributes": True}


class AssignmentCreate(BaseModel):
    """Scope is derived from the subject; clients only choose faculty, subject and section."""

    faculty_id: UUID
    subject_id: UUID
    section: str | None = None


class AssignmentUpdate(BaseModel):
    branch_id: UUID | None = None
    semester_id: UUID | None = None
    academic_year_id: UUID | None = None
    section: str | None = None
    assignment_status: str | None = None
