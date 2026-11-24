"""Identity models: users, students and faculty."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import TimestampMixin, uuid_pk
from app.models.enums import AccountStatus, EnrollmentStatus, Role
from app.database.session import Base


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(String(32), nullable=False, index=True)
    account_status: Mapped[AccountStatus] = mapped_column(
        String(32), default=AccountStatus.ACTIVE, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    student: Mapped["Student | None"] = relationship(back_populates="user", uselist=False)
    faculty: Mapped["Faculty | None"] = relationship(back_populates="user", uselist=False)


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    roll_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("departments.id"))
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("branches.id"))
    current_semester: Mapped[int] = mapped_column(default=1, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    admission_year: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    enrollment_status: Mapped[EnrollmentStatus] = mapped_column(
        String(32), default=EnrollmentStatus.ACTIVE, nullable=False
    )
    section: Mapped[str | None] = mapped_column(String(32))

    user: Mapped[User] = relationship(back_populates="student")
    department: Mapped["Department | None"] = relationship()
    branch: Mapped["Branch | None"] = relationship()


class Faculty(Base, TimestampMixin):
    __tablename__ = "faculty"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    faculty_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("departments.id"))
    designation: Mapped[str] = mapped_column(String(100), nullable=False, default="Faculty")
    account_status: Mapped[AccountStatus] = mapped_column(
        String(32), default=AccountStatus.ACTIVE, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="faculty")
    department: Mapped["Department | None"] = relationship()
