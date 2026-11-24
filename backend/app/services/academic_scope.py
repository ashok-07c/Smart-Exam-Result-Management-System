"""Shared academic scoping rules.

The server resolves a subject's branch/department from
``Subject -> Course -> Branch -> Department``. These helpers are used by both
student eligibility and faculty access checks so a client cannot widen scope
by omitting or overriding a form field.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.academic import Branch, Course, Semester, Subject
from app.models.user import Student


def subject_branch_id(db: Session, subject: Subject) -> UUID | None:
    if not subject.course_id:
        return None
    course = db.get(Course, subject.course_id)
    return course.branch_id if course else None


def subject_department_id(db: Session, subject: Subject) -> UUID | None:
    branch_id = subject_branch_id(db, subject)
    if not branch_id:
        return None
    branch = db.get(Branch, branch_id)
    return branch.department_id if branch else None


def subject_semester_number(db: Session, subject: Subject) -> int | None:
    if not subject.semester_id:
        return None
    semester = db.get(Semester, subject.semester_id)
    return semester.semester_number if semester else None


def resolve_subject_scope(db: Session, subject: Subject) -> tuple[UUID | None, UUID | None, int | None]:
    """Return ``(department_id, branch_id, semester_number)`` for a subject."""
    return (
        subject_department_id(db, subject),
        subject_branch_id(db, subject),
        subject_semester_number(db, subject),
    )


def subject_belongs_to_student(db: Session, subject: Subject, student: Student) -> bool:
    """A student may only write subjects in their current semester and own branch."""
    department_id, branch_id, semester_number = resolve_subject_scope(db, subject)
    if semester_number is not None and semester_number != student.current_semester:
        return False
    if student.branch_id and branch_id and branch_id != student.branch_id:
        return False
    if student.department_id and department_id and department_id != student.department_id:
        return False
    return True
