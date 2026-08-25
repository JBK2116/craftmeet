import datetime
import uuid
from dataclasses import dataclass
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator
from starlette.websockets import WebSocket

from src.constants import MAX_CHAT_LENGTH, MAX_USERNAME_LENGTH, MIN_USERNAME_LENGTH
from src.live.types import InboundMessageTypes, Mood
from src.meeting.schemas import QuestionIn, QuestionOut, ResponseIn


class MeetingSnapshot(BaseModel):
    """Current snapshot of a live meeting

    Attributes:
        mood: Mood of the live meeting
        attention_flag: Things that need attention
        suggested_question_prompt: Next suggested question prompt
        created_at: Snapshots created at time

    """

    mood: Mood
    attention_flag: str
    suggested_question_prompt: str
    created_at: datetime.datetime


class GetSnapshotPayload(BaseModel):
    """Represents a payload for when requesting a snapshot of a live meeting

    Attributes:
        meeting_id: The meeting to create the snapshot for
    """

    meeting_id: uuid.UUID


class GetSnapshotFailedPayload(BaseModel):
    """Represents a payload for when requesting a snapshot of a live meeting fails

    Attributes:
        detail: The reason for the failure
    """

    detail: str


class GetSnapshotSuccessPayload(BaseModel):
    """Represents a payload for when requesting a snapshot of a live meeting succeeds

    Attributes:
        snapshot: The details of the current snapshot
    """

    snapshot: MeetingSnapshot


class AddQuestionPayload(BaseModel):
    """Represents a add question request sent by the host during a live meeting

    Attributes:
        question: The question to be added
    """

    question: QuestionIn


class AddQuestionSuccessPayload(BaseModel):
    """Represents a success response from an add question request

    Attributes:
        question: The question that has been added
    """

    question: QuestionOut


class AddQuestionFailed(BaseModel):
    """Represents a failure response from an add question request

    Attributes:
        detail: The reason for the failure
    """

    detail: str


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


@dataclass
class ParticipantEntry:
    """Represents a singular participant entry tracked in a live meeting session server-side."""

    participant: Participant
    ws: WebSocket | None = None


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
        started_at: The start time of the current meeting.
    """

    question: QuestionOut | None
    responses: list[ResponseIn]
    participants: list[Participant]
    started_at: datetime.datetime


class ParticipantsStatePayload(BaseModel):
    """Payload for the current snapshot of participants in the meeting.

    Attributes:
        participants: List of participants in the meeting.
    """

    participants: list[Participant]


class ChatMessage(BaseModel):
    """Represents a chat message in the current meeting session.

    Attributes:
        name: The name of the user that sent the message
        u_id: The id of the user that sent the message
        message: The contents of the message
        is_host: Boolean indicating if the chat was sent by a host or participant
        created_at: The time of the message's creation
    """

    name: str = Field(min_length=MIN_USERNAME_LENGTH, max_length=MAX_USERNAME_LENGTH)
    u_id: uuid.UUID
    message: str = Field(min_length=1, max_length=MAX_CHAT_LENGTH)
    is_host: bool = Field(default=False)
    created_at: datetime.datetime = Field(
        init=False, default_factory=lambda: datetime.datetime.now(tz=datetime.UTC)
    )


class ChatStatePayload(BaseModel):
    """Payload for the current snapshot of the meeting chat bar.

    Attributes:
        chats: List of all chats received so far in the meeting.
    """

    chats: list[ChatMessage]


class ChatReceivedPayload(BaseModel):
    """Payload for a chat message received from the frontend.

    Attributes:
        chat: The chat message sent from the frontend
    """

    chat: ChatMessage


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


INBOUND_PAYLOAD_MODELS: dict[InboundMessageTypes, type[BaseModel]] = {
    InboundMessageTypes.GET_SNAPSHOT: GetSnapshotPayload,
    InboundMessageTypes.ADD_QUESTION: AddQuestionPayload,
    InboundMessageTypes.PARTICIPANT_CONNECTED: ParticipantConnectedPayload,
    InboundMessageTypes.MEETING_STARTED: MeetingStartedPayload,
    InboundMessageTypes.NEXT_QUESTION: NextQuestionPayload,
    InboundMessageTypes.RESPONSE_RECEIVED: ResponseReceivedPayload,
    InboundMessageTypes.CHAT_RECEIVED: ChatReceivedPayload,
    InboundMessageTypes.REVEAL: RevealMeetingPayload,
}
