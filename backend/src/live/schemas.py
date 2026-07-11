import uuid
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator

from src.constants import MAX_USERNAME_LENGTH, MIN_USERNAME_LENGTH
from src.live.types import InboundMessageTypes, OutboundMessageTypes
from src.meeting.schemas import QuestionOut, ResponseIn


class Participant(BaseModel):
    """Represents a participant in a live meeting session.

    Attributes:
        id: Unique identifier for the participant.
        username: The display name of the participant.
        connected: Whether the participant is currently connected.
        has_answered: Whether the participant has submitted an answer to the current question.
    """

    id: uuid.UUID
    username: str
    connected: bool
    has_answered: bool


class ParticipantConnectedPayload(BaseModel):
    """Payload for when a participant connects.

    Attributes:
        username: The username of the joining participant

    Note:
        The participant ID is retrieved from their access token

    """

    username: str = Field(
        min_length=MIN_USERNAME_LENGTH, max_length=MAX_USERNAME_LENGTH
    )


class ParticipantDisconnectedPayload(BaseModel):
    """Payload for when a participant disconnects"""

    id: uuid.UUID


class WebIn(BaseModel):
    """
    Incoming WebSocket message model.

    Attributes:
        type: The type of the WebSocket message.
        payload: The payload of the message as a dictionary.
    """

    type: InboundMessageTypes
    payload: Any = None  # raw dict when received, parsed into appropriate type after validation; None for types without a payload

    @model_validator(mode="after")
    def _parse_payload_type(self: Self) -> "WebIn":
        if self.payload is None:
            return self
        model = INBOUND_PAYLOAD_MODELS.get(self.type)
        if model is not None:
            self.payload = model(**self.payload)
        return self


class MeetingStatePayload(BaseModel):
    """Payload for the current snapshot of the meeting state.

    Attributes:
        question: The current question being discussed or None if the meeting has not started
        responses: List of responses received so far.
        participants: List of participants in the meeting.
    """

    question: QuestionOut | None
    responses: list[ResponseIn]
    participants: list[Participant]


class MeetingStartedPayload(BaseModel):
    """Payload for when a meeting has started.

    Attributes:
        question: The current question associated with the meeting start.
    """

    question: QuestionOut


class NextQuestionPayload(BaseModel):
    """Payload for when moving to the next question.

    Attributes:
        question: The next question to be presented.
    """

    question: QuestionOut


class CurrentQuestionPayload(BaseModel):
    """Payload for managing the current question

    Attributes:
        question: The current question used in the meeting
    """

    question: QuestionOut


class ResponseReceivedPayload(BaseModel):
    """Payload for receiving a participant's response to a question.

    Attributes:
        response: The participant's response, validated against `ResponseIn`.
    """

    response: ResponseIn


class RevealMeetingPayload(BaseModel):
    """Payload for revealing the current responses to participants

    Attributes:
        responses: A list of all current responses to the active meeting question
    """

    responses: list[ResponseIn]


INBOUND_PAYLOAD_MODELS: dict[
    InboundMessageTypes | OutboundMessageTypes, type[BaseModel]
] = {
    InboundMessageTypes.PARTICIPANT_CONNECTED: ParticipantConnectedPayload,
    InboundMessageTypes.MEETING_STARTED: MeetingStartedPayload,
    InboundMessageTypes.NEXT_QUESTION: NextQuestionPayload,
    InboundMessageTypes.RESPONSE_RECEIVED: ResponseReceivedPayload,
    InboundMessageTypes.REVEAL: RevealMeetingPayload,
}
