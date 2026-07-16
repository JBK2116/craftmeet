from pydantic import BaseModel, model_validator

from src.types import QuestionType


class MCOption(BaseModel):
    """A single option in a multiple-choice question summary."""

    label: str
    votes: int
    pct: float


class MCSummary(BaseModel):
    """AI-generated summary details for a multiple-choice question."""

    options: list[MCOption]
    allow_multiple: bool


class YesNoSummary(BaseModel):
    """AI-generated summary details for a yes/no question."""

    yes_count: int
    no_count: int
    yes_pct: float
    no_pct: float


class RatingScaleSummary(BaseModel):
    """AI-generated summary details for a rating-scale question."""

    min: int
    max: int
    average: float
    median: float
    distribution: dict[str, int]


class RankedVotingItem(BaseModel):
    """A single ranked item in a ranked-voting question summary."""

    label: str
    average_rank: float
    first_place_count: int


class RankedVotingSummary(BaseModel):
    """AI-generated summary details for a ranked-voting question."""

    items: list[RankedVotingItem]


class LongAnswerSummary(BaseModel):
    """AI-generated summary details for a long-answer question."""

    themes: list[str]
    sample_size: int


Detail = (
    MCSummary
    | YesNoSummary
    | RatingScaleSummary
    | RankedVotingSummary
    | LongAnswerSummary
)


class QuestionSummary(BaseModel):
    """AI-generated summary for a single meeting question."""

    position: int
    prompt: str
    type: QuestionType
    response_count: int
    response_rate: float
    headline: str
    narrative: str
    details: Detail

    @model_validator(mode="before")
    @classmethod
    def parse_details(cls, values: dict) -> dict:
        """Dispatch ``details`` to the correct model based on ``type``."""
        type_val = values.get("type")
        details = values.get("details", {})
        map_: dict[str, type[BaseModel]] = {
            "multiple_choice": MCSummary,
            "yes_no": YesNoSummary,
            "rating_scale": RatingScaleSummary,
            "ranked_voting": RankedVotingSummary,
            "long_answer": LongAnswerSummary,
        }
        if isinstance(type_val, str) and type_val in map_:
            values["details"] = map_[type_val](**details)
        elif isinstance(type_val, QuestionType) and type_val.value in map_:
            values["details"] = map_[type_val.value](**details)
        return values


class MeetingSummary(BaseModel):
    """Full AI-generated meeting summary returned to the frontend."""

    executive_summary: str
    key_takeaways: list[str]
    participation_insight: str
    questions: list[QuestionSummary]
