"""Global Python Types

Defines the custom types used throughout the application
"""

from enum import StrEnum


class ErrorTypes(StrEnum):
    """Custom error types sent to frontend"""

    USERNAME = "username"
    EMAIL = "email"
    PASSWORD = "password"  # noqa: S105
    TOKEN = "token"  # noqa: S105
    SERVER = "server"


class MeetingPlan(StrEnum):
    """Available subscription plans"""

    FREE = "free"
    PRO = "pro"
    TEAM = "team"


class MeetingStatus(StrEnum):
    """All possible meeting states"""

    DRAFT = "draft"
    LIVE = "live"
    COMPLETED = "completed"


class QuestionType(StrEnum):
    """All possible question types"""

    MULTIPLE_CHOICE = "multiple_choice"
    LONG_ANSWER = "long_answer"
    RANKED_VOTING = "ranked_voting"
    RATING_SCALE = "rating_scale"
    IDEA_UPVOTE = "idea_upvote"
    YES_NO = "yes_no"


class QuestionStatus(StrEnum):
    """All possible question states"""

    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
