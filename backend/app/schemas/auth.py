"""Authentication schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
    remember_me: bool = False


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthUser(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: Role
    account_status: str
    student_id: UUID | None = None
    faculty_id: UUID | None = None
    roll_number: str | None = None
    department: str | None = None
    branch: str | None = None
    semester: int | None = None
    academic_year: str | None = None
    must_change_password: bool = False


class LoginData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class AdminInitiateResetRequest(BaseModel):
    user_id: UUID
    reason: str | None = None


class PasswordResetInitiated(BaseModel):
    token: str  # Returned only in development/testing for local verification.
    expires_at: datetime
    user_id: UUID
    note: str
