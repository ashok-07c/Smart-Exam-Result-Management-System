"""Result, backlog, recounting and notification schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import PublicationStatus, RecountingStatus, ResultStatus


class SubjectResultOut(BaseModel):
    id: UUID
    subject_id: UUID
    subject_code: str | None = None
    subject_name: str | None = None
    credits: int
    internal_marks: float
    external_marks: float
    total_marks: float
    max_marks: int
    grade: str
    grade_point: float
    result_status: ResultStatus

    model_config = {"from_attributes": True}


class SemesterResultOut(BaseModel):
    id: UUID
    student_id: UUID
    semester_number: int
    academic_year_name: str
    sgpa: float | None = None
    cgpa: float | None = None
    total_credits: int
    earned_credits: int
    status: PublicationStatus
    published_at: datetime | None = None
    subject_results: list[SubjectResultOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SgpaPoint(BaseModel):
    semester: int
    academic_year: str
    sgpa: float | None
    cgpa: float | None
    status: PublicationStatus


class PerformanceOut(BaseModel):
    semesters: list[SgpaPoint]
    current_cgpa: float | None


class BacklogOut(BaseModel):
    id: UUID
    subject_id: UUID
    subject_code: str | None = None
    subject_name: str | None = None
    credits: int | None = None
    semester_number: int
    academic_year_name: str
    attempts: int
    is_cleared: bool
    supplementary_exam_id: UUID | None = None

    model_config = {"from_attributes": True}


class RecountingCreate(BaseModel):
    examination_id: UUID
    subject_id: UUID
    reason: str | None = Field(default=None, max_length=1000)
    result_id: UUID | None = None


class RecountingOut(BaseModel):
    id: UUID
    student_id: UUID
    examination_id: UUID
    subject_id: UUID
    subject_code: str | None = None
    subject_name: str | None = None
    original_marks: float
    reason: str | None = None
    request_status: RecountingStatus
    admin_response: str | None = None
    revised_marks: float | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class RecountingProcess(BaseModel):
    action: str = Field(pattern="^(pending_review|processing|complete|reject)$")
    admin_response: str | None = None
    revised_marks: float | None = Field(default=None, ge=0)


class ResultProcessIn(BaseModel):
    examination_id: UUID
    student_ids: list[UUID] | None = None


class PublicationIn(BaseModel):
    action: str = Field(pattern="^(approve|publish|unpublish)$")
    note: str | None = None
