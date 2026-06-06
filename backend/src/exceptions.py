"""Custom exception types for global use in the application.

This module defines exceptions for handling errors that can happen globally in the application,
for example

    - Database errors
    - User account state issues
"""


class BaseError(Exception):
    """Base custom error type in application"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DatabaseError(BaseError):
    """Database related error"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
