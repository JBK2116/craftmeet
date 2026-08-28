from enum import Enum, StrEnum

from fastapi import status


class CloseCode(Enum):
    """
    Enumeration defining possible WebSocket close codes for the live meeting system.

    Each member is a tuple of (code, message).

    Attributes:
        code: A WebSocket close code (int) indicating the reason for closure.
        message: A descriptive human-readable error message.
    """

    HOST_ALREADY_CONNECTED = (
        status.WS_1008_POLICY_VIOLATION,
        "A host is already connected to the live meeting",
    )
    PARTICIPANT_RECONNECTED_ELSEWHERE = (
        status.WS_1008_POLICY_VIOLATION,
        "A participant has reconnected to this meeting on a new websocket",
    )
    INVALID_TOKEN = (status.WS_1008_POLICY_VIOLATION, "invalid access token provided")
    MEETING_NOT_FOUND = (4001, "meeting not found")

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class Mood(StrEnum):
    """Current mood of a live meeting"""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"
    DISENGAGED = "disengaged"


class InboundMessageTypes(Enum):
    """Enumeration of websocket messages sent from client side"""

    GET_SNAPSHOT = "get_snapshot"  # sent from host
    ADD_QUESTION = "add_question"  # sent from host
    MEETING_STARTED = "meeting_started"  # sent from host
    MEETING_ENDED = "meeting_ended"  # sent from host
    NEXT_QUESTION = "next_question"  # sent from host
    RESPONSE_RECEIVED = "response_received"  # sent from participants
    REVEAL = "reveal"  # sent from host
    PARTICIPANT_CONNECTED = "participant_connected"  # sent from participants
    PARTICIPANT_JOIN_ROOM = "participant_join_room"  # sent from participants
    CHAT_RECEIVED = "chat_received"  # sent from host or participant
    PING = "ping"  # sent from participants (heartbeat)


class OutboundMessageTypes(StrEnum):
    """Enumeration of websocket messages sent from server side"""

    GET_SNAPSHOT_SUCCESS = "get_snapshot_success"  # sent to host
    GET_SNAPSHOT_FAILED = "get_snapshot_failed"  # sent to host
    ADD_QUESTION_SUCCESS = "add_question_success"  # sent to host
    ADD_QUESTION_FAILED = "add_question_failed"  # sent to host
    MEETING_STATE = "meeting_state"  # sent to host
    MEETING_STARTED = "meeting_started"  # sent to participants
    MEETING_ENDED = "meeting_ended"  # sent to participants
    NEXT_QUESTION = "next_question"  # sent to participants
    CURRENT_QUESTION = "current_question"  # sent to participants
    RESPONSE_RECEIVED = "response_received"  # sent to host
    REVEAL = "reveal"  # sent to participants
    HOST_DISCONNECTED = "host_disconnected"  # sent to participants
    HOST_RECONNECTED = "host_reconnected"  # sent to participants
    PARTICIPANT_CONNECTED = "participant_connected"  # sent to host
    PARTICIPANT_DISCONNECTED = "participant_disconnected"  # sent to host
    PARTICIPANT_JOIN_ROOM_SUCCESS = (
        "participant_join_room_success"  # sent to participants
    )
    PARTICIPANT_JOIN_ROOM_FAILED = (
        "participant_join_room_failed"  # sent to participants
    )
    PARTICIPANT_STATE = "participant_state"  # sent to participant
    PARTICIPANTS_STATE = "participants_state"  # sent to participants
    CHAT_RECEIVED = "chat_received"  # sent to host or participant
    CHAT_STATE = "chat_state"  # sent to host or participant
    PONG = "pong"  # sent to participants (heartbeat reply)
