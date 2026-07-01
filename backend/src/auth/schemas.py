"""
Schemas for authentication

Defines Pydantic request/response models used across authentication
flows including signup, login, OAuth, and password reset.
"""

import datetime
import uuid
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)

from src.auth.constants import RESET_PASSWORD_TOKEN_LENGTH, VERIFY_EMAIL_TOKEN_LENGTH
from src.constants import (
    BCRYPT_MAX_BYTES,
    MAX_EMAIL_LENGTH,
    MAX_PASSWORD_LENGTH,
    MAX_USERNAME_LENGTH,
    MIN_EMAIL_LENGTH,
    MIN_PASSWORD_LENGTH,
    MIN_USERNAME_LENGTH,
)
from src.types import MeetingPlan


def validate_username(value: str) -> str:
    if len(value) < MIN_USERNAME_LENGTH:
        raise ValueError(
            f"Username must be at least {MIN_USERNAME_LENGTH} characters long"
        )
    if len(value) > MAX_USERNAME_LENGTH:
        raise ValueError(f"Username must not exceed {MAX_USERNAME_LENGTH} characters")
    if not value.isalnum():
        raise ValueError("Username must contain only alphanumeric characters")
    return value


def validate_email_length(value: str) -> str:
    if len(value) < MIN_EMAIL_LENGTH:
        raise ValueError(f"Email must be at least {MIN_EMAIL_LENGTH} characters long")
    if len(value) > MAX_EMAIL_LENGTH:
        raise ValueError(f"Email must not exceed {MAX_EMAIL_LENGTH} characters")
    return value


def validate_password_length(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
        )
    if len(value) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must not exceed {MAX_PASSWORD_LENGTH} characters")
    return value


def validate_password(value: str) -> str:
    validate_password_length(value)
    if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError("Password is too long")
    if not any(char.isupper() for char in value):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(char.islower() for char in value):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(char.isdigit() for char in value):
        raise ValueError("Password must contain at least one digit")
    if not any(not char.isalnum() for char in value):
        raise ValueError("Password must contain at least one special character")
    return value


class UserOut(BaseModel):
    """Pydantic model representing sqlalchemy user sent to frontend"""

    id: uuid.UUID
    username: str | None
    email: str
    # OAUTH
    google_id: str | None
    # Meeting Stat
    live_meeting: bool
    total_meetings_month: int
    total_meetings: int
    total_participants: int
    meeting_plan: MeetingPlan
    # Verification Status
    verified: bool
    verified_at: datetime.datetime
    # Time
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class SignupRequest(BaseModel):
    """Pydantic model representing signup request body"""

    username: Annotated[str, AfterValidator(validate_username)]
    email: Annotated[EmailStr, AfterValidator(validate_email_length)]
    password: Annotated[str, AfterValidator(validate_password)]


class LoginRequest(BaseModel):
    """Pydantic model representing login request body"""

    email: Annotated[EmailStr, AfterValidator(validate_email_length)]
    password: Annotated[str, AfterValidator(validate_password_length)]


class ForgotPasswordRequest(BaseModel):
    """Pydantic model representing forgot password request"""

    email: Annotated[EmailStr, AfterValidator(validate_email_length)]


class ResetPasswordRequest(BaseModel):
    """Pydantic model representing reset password request"""

    token: str = Field(
        min_length=RESET_PASSWORD_TOKEN_LENGTH, max_length=RESET_PASSWORD_TOKEN_LENGTH
    )
    password: Annotated[str, AfterValidator(validate_password)]
    confirm_password: Annotated[str, AfterValidator(validate_password_length)]

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.password != self.confirm_password:
            raise ValueError("Passwords don't match")
        return self


class VerifyEmailRequest(BaseModel):
    """Pydantic model representing verify email request body"""

    token: str = Field(
        min_length=VERIFY_EMAIL_TOKEN_LENGTH, max_length=VERIFY_EMAIL_TOKEN_LENGTH
    )


class MeRequest(BaseModel):
    """Pydantic model representing user update request body"""

    username: Annotated[str, AfterValidator(validate_username)]
