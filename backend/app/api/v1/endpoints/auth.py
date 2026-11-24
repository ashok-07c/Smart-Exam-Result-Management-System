"""Authentication endpoints. Role is always read from the database, never from the client."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe

import jwt
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import UnauthorizedError, ValidationError
from app.core.responses import ok
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.enums import AccountStatus
from app.models.misc import PasswordResetToken
from app.models.user import Faculty, Student, User
from app.schemas.auth import ChangePasswordRequest, ForgotPasswordRequest, LoginRequest, ResetPasswordRequest
from app.services.audit import log_action

router = APIRouter()


def _auth_user(db: Session, user: User) -> dict:
    student = db.query(Student).filter(Student.user_id == user.id).first()
    faculty = db.query(Faculty).filter(Faculty.user_id == user.id).first()
    department = None
    branch = None
    semester = None
    academic_year = None
    if student:
        department = student.department.department_name if student.department else None
        branch = student.branch.branch_name if student.branch else None
        semester = student.current_semester
        academic_year = student.academic_year
    if faculty:
        department = faculty.department.department_name if faculty.department else None
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "account_status": user.account_status,
        "student_id": student.id if student else None,
        "faculty_id": faculty.id if faculty else None,
        "roll_number": student.roll_number if student else None,
        "department": department,
        "branch": branch,
        "semester": semester,
        "academic_year": academic_year,
        "must_change_password": bool(user.must_change_password),
    }


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=f"{settings.api_prefix}/auth",
    )


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: DbSession) -> dict:
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    if user.account_status != AccountStatus.ACTIVE:
        raise UnauthorizedError("This account is not active")
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    access = create_token(str(user.id), "access")
    refresh = create_token(str(user.id), "refresh")
    _set_refresh_cookie(response, refresh)
    log_action(db, user=user, action="LOGIN", entity_type="User", entity_id=str(user.id), commit=True)
    return ok(
        {
            "access_token": access,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "user": _auth_user(db, user),
        },
        "Login successful",
    )


@router.post("/logout")
def logout(response: Response, user: CurrentUser, db: DbSession) -> dict:
    response.delete_cookie(settings.refresh_cookie_name, path=f"{settings.api_prefix}/auth")
    log_action(db, user=user, action="LOGOUT", entity_type="User", entity_id=str(user.id), commit=True)
    return ok(message="Logged out successfully")


@router.post("/refresh")
def refresh(request: __import__("fastapi").Request, response: Response, db: DbSession) -> dict:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise UnauthorizedError("No refresh token supplied")
    try:
        payload = decode_token(token, "refresh")
        user = db.get(User, __import__("uuid").UUID(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise UnauthorizedError("Invalid or expired refresh token")
    if not user or user.account_status != AccountStatus.ACTIVE:
        raise UnauthorizedError("Account is no longer active")
    new_refresh = create_token(str(user.id), "refresh")
    _set_refresh_cookie(response, new_refresh)
    return ok(
        {
            "access_token": create_token(str(user.id), "access"),
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "user": _auth_user(db, user),
        },
        "Token refreshed",
    )


@router.get("/me")
def me(user: CurrentUser, db: DbSession) -> dict:
    return ok(_auth_user(db, user), "Current user")


def _validate_new_password(current: str, new: str, confirm: str) -> None:
    if new != confirm:
        raise ValidationError("New password and confirmation do not match")
    if new == current:
        raise ValidationError("New password must be different from the current password")
    if len(new) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if not any(c.isupper() for c in new) or not any(c.islower() for c in new) or not any(c.isdigit() for c in new):
        raise ValidationError("Password must include an uppercase letter, a lowercase letter and a digit")


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, user: CurrentUser, db: DbSession) -> dict:
    """Mandatory first-login password change for temporary student passwords."""
    if not verify_password(payload.current_password, user.password_hash):
        raise ValidationError("Current password is incorrect")
    _validate_new_password(payload.current_password, payload.new_password, payload.confirm_password)
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    log_action(
        db, user=user, action="TEMPORARY_PASSWORD_CHANGED", entity_type="User",
        entity_id=str(user.id),
    )
    db.commit()
    return ok({"must_change_password": False}, "Password changed successfully")


def _issue_reset_token(db: Session, user: User, requested_by: User | None = None) -> tuple[str, datetime]:
    token = token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=sha256(token.encode()).hexdigest(),
            expires_at=expires,
            requested_by=requested_by.id if requested_by else None,
        )
    )
    db.commit()
    return token, expires


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: DbSession) -> dict:
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user:
        # Do not disclose account existence.
        return ok(message="If the account exists, a reset link has been issued")
    token, _ = _issue_reset_token(db, user)
    # No email provider is configured; the token is returned in development/testing only
    # so the workflow can be verified locally. In production it must be delivered out-of-band.
    if settings.environment == "production":
        return ok(message="If the account exists, a reset link has been issued")
    return ok({"reset_token": token}, "Password reset token issued (development mode)")


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: DbSession) -> dict:
    token_hash = sha256(payload.token.encode()).hexdigest()
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used_at.is_(None),
    ).first()
    if not record:
        raise ValidationError("Reset token is invalid or expired")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise ValidationError("Reset token is invalid or expired")
    user = db.get(User, record.user_id)
    if not user:
        raise ValidationError("Reset token is invalid")
    user.password_hash = hash_password(payload.new_password)
    record.used_at = datetime.now(timezone.utc)
    db.commit()
    log_action(db, user=user, action="PASSWORD_RESET_COMPLETED", entity_type="User", entity_id=str(user.id), commit=True)
    return ok(message="Password has been reset")
