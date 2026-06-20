"""Meeting-related exception types

This module defines exceptions for meeting management errors, including:
- Meeting lookup failures (e.g., meeting not found)
- Meeting validation and state errors
"""

from src.exceptions import BaseError


class MeetingNotFoundError(BaseError):
    """Meeting not found in database"""

    def __init__(self, m_id: str) -> None:
        super().__init__(f"meeting with id: {m_id} not found")
