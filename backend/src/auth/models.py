"""Authentication SQLAlchemy ORM models

Stores models for authentication-related functionality including email verification
tokens, password reset tokens, and other auth-related data structures.
"""

import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.auth.constants import (
    TOKEN_HASH_LENGTH_EMAIL_VERIFY,
    TOKEN_HASH_LENGTH_REFRESH_TOKEN,
    TOKEN_HASH_LENGTH_RESET_PASSWORD_TOKEN,
)
from src.models import BaseClass


class VerifyEmailToken(BaseClass):
    """Verify Email Token Model"""

    # Unique identifier for this token record
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the user this token belongs to
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Hashed token value for secure storage
    token_hash: Mapped[str] = mapped_column(
        String(TOKEN_HASH_LENGTH_EMAIL_VERIFY), unique=True
    )
    # Timestamp when this token expires
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Timestamp when this token was used, null if not yet used
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ResetPasswordToken(BaseClass):
    """Reset Password Token Model"""

    # Unique identifier for this token record
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the user this token belongs to
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Hashed token value for secure storage
    token_hash: Mapped[str] = mapped_column(
        String(TOKEN_HASH_LENGTH_RESET_PASSWORD_TOKEN), unique=True
    )
    # Timestamp when this token expires
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Timestamp when this token was used, null if not yet used
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RefreshToken(BaseClass):
    """Refresh Token Model"""

    # Unique identifier for this token record
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Foreign key reference to the user this token belongs to
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE")
    )
    # Hashed token value for secure storage
    token_hash: Mapped[str] = mapped_column(
        String(TOKEN_HASH_LENGTH_REFRESH_TOKEN), unique=True
    )
    # Timestamp when this token expires
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
