"""Academic structure models."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import JSON, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.common import TimestampMixin, uuid_pk
from app.models.enums import SubjectType


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = uuid_pk()
    department_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)


class Branch(Base, TimestampMixin):
    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = uuid_pk()
    branch_name: Mapped[str] = mapped_column(String(200), nullable=False)
    branch_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("departments.id"))


class AcademicYear(Base, TimestampMixin):
    __tablename__ = "academic_years"

    id: Mapped[uuid.UUID] = uuid_pk()
    academic_year_name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    start_date: Mapped[date | None] = mapped_column()
    end_date: Mapped[date | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)


class Regulation(Base, TimestampMixin):
    """Academic regulation identity.

    Grade and pass rules are no longer configured here: they are centralized in
    ``app.services.grading``. The JSON columns are retained only so historical
    records remain readable; they are not consulted by result processing.
    """

    __tablename__ = "regulations"

    id: Mapped[uuid.UUID] = uuid_pk()
    regulation_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    effective_year: Mapped[str] = mapped_column(String(32), nullable=False)
    grade_rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    pass_rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    calculation_rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class Semester(Base, TimestampMixin):
    __tablename__ = "semesters"

    id: Mapped[uuid.UUID] = uuid_pk()
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("academic_years.id"))
    regulation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("regulations.id"))


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = uuid_pk()
    course_name: Mapped[str] = mapped_column(String(200), nullable=False)
    course_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("branches.id"))
    regulation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("regulations.id"))
    duration_years: Mapped[int] = mapped_column(Integer, default=4, nullable=False)


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = uuid_pk()
    subject_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    subject_name: Mapped[str] = mapped_column(String(200), nullable=False)
    course_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("courses.id"))
    semester_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("semesters.id"))
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    internal_max_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    external_max_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=70)
    subject_type: Mapped[SubjectType] = mapped_column(String(32), default=SubjectType.THEORY, nullable=False)
    assessment_configuration: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class FacultyAssignment(Base, TimestampMixin):
    __tablename__ = "faculty_assignments"

    id: Mapped[uuid.UUID] = uuid_pk()
    faculty_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("faculty.id"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("branches.id"))
    semester_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("semesters.id"))
    academic_year_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("academic_years.id"))
    section: Mapped[str | None] = mapped_column(String(32))
    assignment_status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    faculty: Mapped["Faculty"] = relationship()
    subject: Mapped[Subject] = relationship()
