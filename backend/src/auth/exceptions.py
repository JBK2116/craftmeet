"""Custom exception types for authentication-related logic

This module defines exceptions for handling authentication errors, including:
- Authentication failures and invalid credentials
- Email validation and delivery errors
- User account state issues (e.g., email already exists)
- Token and session management errors
"""

from src.exceptions import BaseError


class EmailExistsError(BaseError):
    """Email already exists with a verified user error"""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(
            f"email: {email} already exists in the database with a verified user"
        )


class EmailDeliveryError(BaseError):
    """Email delivery failed error"""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"failed to send verification email to: {email}")


class EmailNotVerifiedError(BaseError):
    """Email is not verified error"""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"user with email: {email} has not verified their account")


class VerifyEmailTokenCooldownError(BaseError):
    """Verify Email Token Cooldown error"""

    def __init__(self, email: str) -> None:
        super().__init__(
            f"verify email token cooldown period has not elapsed for user: {email}"
        )


class UserNotFoundError(BaseError):
    """User not found in database"""

    def __init__(self, email: str) -> None:
        super().__init__(f"invalid password for user with email: {email}")


class UserInvalidPasswordError(BaseError):
    """User password is invalid eor"""

    def __init__(self, email: str) -> None:
        super().__init__(f"invalid password provided for user with email: {email}")


class InvalidTokenError(BaseError):
    """Invalid token provided to backend error"""

    def __init__(self) -> None:
        super().__init__("invalid token provided to backend")
