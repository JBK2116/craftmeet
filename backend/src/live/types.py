from enum import Enum

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
        status.WS_1000_NORMAL_CLOSURE,
        "A participant has reconnected to this meeting on a new websocket",
    )
    INVALID_TOKEN = (status.WS_1008_POLICY_VIOLATION, "invalid access token provided")

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class InboundMessageTypes(Enum):
    """Enumeration of websocket messages sent from client side"""

    MEETING_STARTED = "meeting_started"  # sent from host
    MEETING_ENDED = "meeting_ended"  # sent from host
    NEXT_QUESTION = "next_question"  # sent from host
    RESPONSE_RECEIVED = "response_received"  # sent from participants
    REVEAL = "reveal"  # sent from host
    PARTICIPANT_CONNECTED = "participant_connected"  # sent from participants


class OutboundMessageTypes(Enum):
    """Enumeration of websocket messages sent from server side"""

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
    PARTICIPANT_STATE = "participant_state"  # sent to participant

    def __init__(self, type: str):
        """Initialize the message type.

        Args:
            type: The string representation of the message type.
        """
        self.type = type
