"""Notification targeting and delivery service."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.academic import Branch, Semester
from app.models.enums import AudienceType, NotificationCategory, Role
from app.models.notification import Notification, NotificationRecipient
from app.models.user import Faculty, Student, User
from app.schemas.notification import NotificationCreate


def resolve_recipients(db: Session, payload: NotificationCreate) -> list[User]:
    audience = payload.audience_type
    query = db.query(User).filter(User.account_status == "ACTIVE")

    if audience == AudienceType.SPECIFIC_USERS:
        ids = payload.recipient_user_ids or []
        return query.filter(User.id.in_(ids)).all() if ids else []
    if audience == AudienceType.ALL:
        return query.all()

    role = Role.FACULTY if audience == AudienceType.ALL_FACULTY else Role.STUDENT
    query = query.filter(User.role == role)

    if audience == AudienceType.SPECIFIC_BRANCH and payload.branch_id:
        student_ids = db.query(Student.user_id).filter(Student.branch_id == payload.branch_id)
        faculty_ids = db.query(Faculty.user_id).filter(Faculty.department_id.in_(
            db.query(Branch.department_id).filter(Branch.id == payload.branch_id)
        ))
        query = query.filter(or_(User.id.in_(student_ids), User.id.in_(faculty_ids)))
    if audience == AudienceType.SPECIFIC_SEMESTER and payload.semester_id:
        student_ids = db.query(Student.user_id).filter(Student.current_semester == db.get(Semester, payload.semester_id).semester_number)
        query = query.filter(User.id.in_(student_ids))
    if audience == AudienceType.SPECIFIC_CLASS:
        if payload.branch_id:
            student_ids = db.query(Student.user_id).filter(Student.branch_id == payload.branch_id)
            query = query.filter(User.id.in_(student_ids))
        if payload.section:
            section_ids = db.query(Student.user_id).filter(Student.section == payload.section)
            query = query.filter(User.id.in_(section_ids))
    return query.all()


def create_notification(
    db: Session, payload: NotificationCreate, sender: User, *, commit: bool = True
) -> Notification:
    recipients = resolve_recipients(db, payload)
    notification = Notification(
        title=payload.title,
        message=payload.message,
        category=payload.category,
        sender_id=sender.id,
        audience_type=payload.audience_type,
        branch_id=payload.branch_id,
        semester_id=payload.semester_id,
        academic_year_id=payload.academic_year_id,
        section=payload.section,
        published_at=datetime.now(timezone.utc) if payload.publish else None,
    )
    db.add(notification)
    db.flush()
    for user in recipients:
        db.add(NotificationRecipient(notification_id=notification.id, recipient_user_id=user.id))
    if commit:
        db.commit()
        db.refresh(notification)
    return notification


def notify_users(
    db: Session,
    *,
    sender: User,
    user_ids: list[UUID],
    title: str,
    message: str,
    category: NotificationCategory,
) -> Notification | None:
    unique_ids = list(dict.fromkeys(user_ids))
    if not unique_ids:
        return None
    payload = NotificationCreate(
        title=title,
        message=message,
        category=category,
        audience_type=AudienceType.SPECIFIC_USERS,
        recipient_user_ids=unique_ids,
        publish=True,
    )
    return create_notification(db, payload, sender, commit=True)
