"""Meeting-related exception types

This module defines exceptions for meeting management errors, including:
- Meeting lookup failures (e.g., meeting not found)
- Meeting validation and state errors
"""

from src.exceptions import BaseError


class MeetingNotFoundError(BaseError):
    """Meeting not found in database"""

    def __init__(self, m_id: str | None = None) -> None:
        if m_id:
            super().__init__(f"meeting with id: {m_id} not found")
        else:
            super().__init__("meeting not found")


class MeetingNotLiveError(BaseError):
    """Meeting is not live"""

    def __init__(self) -> None:
        super().__init__("meeting is not live")
