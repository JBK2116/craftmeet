"""
Schemas for authentication

Defines Pydantic request/response models used across authentication
flows including signup, login, OAuth, and password reset.
"""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

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

    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if len(value) < MIN_USERNAME_LENGTH:
            raise ValueError(
                f"Username must be at least {MIN_USERNAME_LENGTH} characters long"
            )
        if len(value) > MAX_USERNAME_LENGTH:
            raise ValueError(
                f"Username must not exceed {MAX_USERNAME_LENGTH} characters"
            )
        if not value.isalnum():
            raise ValueError("Username must contain only alphanumeric characters")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if len(value) < MIN_EMAIL_LENGTH:
            raise ValueError(
                f"Email must be at least {MIN_EMAIL_LENGTH} characters long"
            )
        if len(value) > MAX_EMAIL_LENGTH:
            raise ValueError(f"Email must not exceed {MAX_EMAIL_LENGTH} characters")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
            )
        if len(value) > MAX_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must not exceed {MAX_PASSWORD_LENGTH} characters"
            )
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


class LoginRequest(BaseModel):
    """Pydantic model representing login request body"""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if len(value) < MIN_EMAIL_LENGTH:
            raise ValueError(
                f"Email must be at least {MIN_EMAIL_LENGTH} characters long"
            )
        if len(value) > MAX_EMAIL_LENGTH:
            raise ValueError(f"Email must not exceed {MAX_EMAIL_LENGTH} characters")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
            )
        if len(value) > MAX_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must not exceed {MAX_PASSWORD_LENGTH} characters"
            )
        return value
