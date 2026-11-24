"""Audit sensitive operations. Audit rows are append-only through the API."""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification import AuditLog
from app.models.user import User


def log_action(
    db: Session,
    *,
    user: User | None,
    action: str,
    entity_type: str,
    entity_id: str | UUID | None = None,
    previous: Any = None,
    new: Any = None,
    request_context: str | None = None,
    commit: bool = False,
) -> AuditLog:
    def serialize(value: Any) -> str | None:
        if value is None:
            return None
        try:
            return json.dumps(value, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)

    entry = AuditLog(
        user_id=user.id if user else None,
        user_role=str(getattr(user.role, "value", user.role)) if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        previous_value=serialize(previous),
        new_value=serialize(new),
        request_context=request_context,
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry
