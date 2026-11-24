"""Shared notification inbox actions."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, get_pagination
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.responses import ok
from app.models.notification import Notification, NotificationRecipient

router = APIRouter()


def _assert_owner(db: Session, recipient_id: UUID, user_id: UUID) -> NotificationRecipient:
    record = db.get(NotificationRecipient, recipient_id)
    if not record or record.recipient_user_id != user_id:
        raise NotFoundError("Notification not found")
    return record


@router.patch("/{recipient_id}/read")
def mark_read(recipient_id: UUID, user: CurrentUser, db: DbSession) -> dict:
    record = _assert_owner(db, recipient_id, user.id)
    record.read_at = datetime.now(timezone.utc)
    db.commit()
    return ok(message="Notification marked as read")


@router.post("/mark-all-read")
def mark_all_read(user: CurrentUser, db: DbSession) -> dict:
    rows = (
        db.query(NotificationRecipient)
        .filter(NotificationRecipient.recipient_user_id == user.id, NotificationRecipient.read_at.is_(None))
        .all()
    )
    for row in rows:
        row.read_at = datetime.now(timezone.utc)
    db.commit()
    return ok({"updated": len(rows)}, "All notifications marked as read")


@router.get("/unread-count")
def unread_count(user: CurrentUser, db: DbSession) -> dict:
    count = (
        db.query(NotificationRecipient)
        .filter(
            NotificationRecipient.recipient_user_id == user.id,
            NotificationRecipient.read_at.is_(None),
        )
        .count()
    )
    return ok({"count": count}, "Unread notification count")


@router.get("")
def my_notifications(
    user: CurrentUser, db: DbSession, category: str | None = None,
    unread_only: bool = False, page: int = 1, page_size: int = 20,
) -> dict:
    page, page_size = get_pagination(page, page_size)
    query = (
        db.query(NotificationRecipient)
        .join(Notification, NotificationRecipient.notification_id == Notification.id)
        .filter(NotificationRecipient.recipient_user_id == user.id)
    )
    if category:
        query = query.filter(Notification.category == category)
    if unread_only:
        query = query.filter(NotificationRecipient.read_at.is_(None))
    total = query.count()
    rows = query.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "items": [
            {
                "id": r.id,
                "notification_id": r.notification_id,
                "title": r.notification.title,
                "message": r.notification.message,
                "category": r.notification.category,
                "sender_id": r.notification.sender_id,
                "created_at": r.notification.created_at,
                "published_at": r.notification.published_at,
                "read": r.read_at is not None,
                "read_at": r.read_at,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }, "Notifications")
