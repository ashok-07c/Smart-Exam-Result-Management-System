"""FastAPI dependencies for authentication and role/assignment authorization."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError, PasswordChangeRequiredError, UnauthorizedError
from app.core.security import decode_token
from app.database.session import get_db
from app.models.enums import AccountStatus, Role
from app.models.user import Faculty, Student, User

bearer = HTTPBearer(auto_error=False, description="JWT access token")


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if not credentials:
        # Support access token in cookie for browser flows where Authorization is unavailable.
        token = None
    else:
        token = credentials.credentials
    if not token:
        raise UnauthorizedError("Authentication required")
    try:
        payload = decode_token(token, "access")
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise UnauthorizedError("Invalid or expired access token")
    user = db.get(User, user_id)
    if not user:
        raise UnauthorizedError("User no longer exists")
    if user.account_status != AccountStatus.ACTIVE:
        raise ForbiddenError("Account is not active")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def require_roles(*roles: Role):
    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("Your role cannot perform this action")
        return user

    return dependency


def get_current_student(user: CurrentUser, db: DbSession) -> Student:
    if user.role != Role.STUDENT:
        raise ForbiddenError("Student access required")
    if user.must_change_password:
        raise PasswordChangeRequiredError()
    student = db.query(Student).filter(Student.user_id == user.id).first()
    if not student or student.enrollment_status != "ACTIVE":
        raise ForbiddenError("Student record is not active")
    return student


def get_current_faculty(user: CurrentUser, db: DbSession) -> Faculty:
    if user.role != Role.FACULTY:
        raise ForbiddenError("Faculty access required")
    faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first()
    if not faculty or faculty.account_status != AccountStatus.ACTIVE:
        raise ForbiddenError("Faculty record is not active")
    return faculty


CurrentStudent = Annotated[Student, Depends(get_current_student)]
CurrentFaculty = Annotated[Faculty, Depends(get_current_faculty)]


def require_exam_admin(user: CurrentUser) -> User:
    if user.role != Role.EXAM_ADMIN:
        raise ForbiddenError("Examination administrator access required")
    return user


ExamAdmin = Annotated[User, Depends(require_exam_admin)]


def get_pagination(page: int = 1, page_size: int = 20) -> tuple[int, int]:
    if page < 1:
        page = 1
    page_size = max(1, min(200, page_size))
    return page, page_size


def get_or_404(db: Session, model, object_id: UUID):
    obj = db.get(model, object_id)
    if not obj:
        raise NotFoundError(f"{model.__name__} not found")
    return obj
