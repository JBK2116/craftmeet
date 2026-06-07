"""Global Python Types

Defines the custom types used throughout the application
"""

from enum import Enum, StrEnum


class ErrorTypes(Enum):
    USERNAME = ("username", "Invalid username.")
    EMAIL = ("email", "Invalid email address.")
    EMAIL_ALREADY_EXISTS = (
        "email_already_exists",
        "An account with this email already exists.",
    )
    PASSWORD = ("password", "Invalid password.")
    TOKEN = ("token", "Invalid or expired token.")
    VERIFY_EMAIL_TOKEN_COOLDOWN = (
        "verify_email_token_cooldown",
        "Please wait at least a minute before requesting another verification email.",
    )
    SERVER = ("server", "An unexpected server error occurred.")

    def __init__(self, type: str, message: str):
        self.type = type
        self.message = message


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
