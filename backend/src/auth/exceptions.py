"""Custom exception types for authentication-related logic

This module defines exceptions for handling authentication errors, including:
- Authentication failures and invalid credentials
- Email validation and delivery errors
- User account state issues (e.g., email already exists)
- Token and session management errors
"""

from src.exceptions import BaseError


class EmailExistsError(BaseError):
    """Email already exists error"""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"email: {email} already exists in the database")


class EmailDeliveryError(BaseError):
    """Email delivery failed error"""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"failed to send verification email to: {email}")
