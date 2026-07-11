import asyncio
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket, status

from src.live.schemas import (
    CurrentQuestionPayload,
    MeetingStartedPayload,
    MeetingStatePayload,
    NextQuestionPayload,
    Participant,
    ParticipantConnectedPayload,
    ParticipantDisconnectedPayload,
    ResponseReceivedPayload,
    RevealMeetingPayload,
)
from src.live.service import LiveService
from src.live.types import CloseCode, OutboundMessageTypes
from src.utils import set_timeout


@dataclass
class ParticipantEntry:
    participant: Participant
    ws: WebSocket | None = None


class LiveRoom:
    def __init__(self, room_id: uuid.UUID, host: WebSocket):
        self.room_id = (
            room_id  # Unique identifier for the room equivalent to meeting id
        )
        self.host: WebSocket | None = (
            host  # host websocket connection, becomes None on disconnects/connection drops
        )
        self.participants: dict[
            uuid.UUID, ParticipantEntry
        ] = {}  # all connected participants
        self.service = LiveService(
            host_id=host.state.user.id, meeting_id=room_id
        )  # service layer for business logic
        self.meeting_timer: asyncio.Task | None = (
            None  # timer to auto terminate meeting
        )

    async def reconnect_host(self, ws: WebSocket) -> None:
        """Reconnect the host to the current meeting"""
        self.host = ws
        data = MeetingStatePayload(
            question=self.service.current_question,
            responses=self.service.get_current_responses(),
            participants=[p.participant for p in self.participants.values()],
        )
        await self.host.send_json(data=data.model_dump(mode="json"))
        await self._broadcast(
            task=_send_message, message={"type": OutboundMessageTypes.HOST_RECONNECTED}
        )

    async def host_disconnected(self):
        """Send the host disconnected signal to all connected participants"""
        await self._broadcast(
            task=_send_message, message={"type": OutboundMessageTypes.HOST_DISCONNECTED}
        )

    async def start_meeting_timer(self) -> None:
        """Starts a timer to automatically end the meeting after its duration has elapsed"""
        duration = await self.service.get_meeting_duration()
        self.meeting_timer = set_timeout(self.end_meeting, delay_seconds=duration * 60)

    async def start_meeting(self, payload: MeetingStartedPayload) -> None:
        """Send the start meeting signal to all connected participants."""
        self.service.current_question = payload.question
        await self.service.start_meeting()
        await self.start_meeting_timer()
        await self._broadcast(
            task=_send_message,
            message={
                "type": OutboundMessageTypes.MEETING_STARTED,
                "payload": payload.model_dump(mode="json"),
            },
        )

    async def next_question(self, payload: NextQuestionPayload) -> None:
        """Send the next meeting question to all connected participants."""
        self.service.current_question = payload.question
        for p in self.participants.values():
            p.participant.has_answered = False
        await self._broadcast(
            task=_send_message,
            message={
                "type": OutboundMessageTypes.NEXT_QUESTION,
                "payload": payload.model_dump(mode="json"),
            },
        )

    async def end_stale_meeting(self) -> None:
        """End a stale meeting and close all connected participant websockets."""
        if self.meeting_timer is not None:
            self.meeting_timer.cancel()
        await self.service.end_stale_meeting()
        await self._broadcast(task=_send_close)

    async def end_meeting(self) -> None:
        """End a meeting and close all connected participant websockets"""
        if self.meeting_timer is not None:
            self.meeting_timer.cancel()
        # TODO: Call the service to handle the underlying logic
        await self._broadcast(
            task=_send_message, message={"type": OutboundMessageTypes.MEETING_ENDED}
        )

    async def participant_connected(
        self, payload: ParticipantConnectedPayload, p_id: uuid.UUID, ws: WebSocket
    ) -> None:
        """Add a connected participant to the meeting"""
        existing = self.participants.get(p_id, None)
        if existing:
            old_ws = existing.ws
            existing.participant.username = payload.username
            existing.participant.connected = True
            existing.ws = ws
            if old_ws and old_ws is not ws:
                await old_ws.close(
                    code=CloseCode.PARTICIPANT_RECONNECTED_ELSEWHERE.code,
                    reason=CloseCode.PARTICIPANT_RECONNECTED_ELSEWHERE.message,
                )

        else:
            new_participant = Participant(
                id=p_id,
                username=payload.username,
                connected=True,
                has_answered=False,
            )
            self.participants[p_id] = ParticipantEntry(
                participant=new_participant, ws=ws
            )
        asyncio.create_task(
            ws.send_json(
                {
                    "type": OutboundMessageTypes.PARTICIPANT_STATE,
                    "payload": self.participants[p_id].participant.model_dump(
                        mode="json"
                    ),
                }
            )
        )
        if self.service.current_question is not None:
            asyncio.create_task(
                ws.send_json(
                    {
                        "type": OutboundMessageTypes.CURRENT_QUESTION,
                        "payload": CurrentQuestionPayload(
                            question=self.service.current_question
                        ).model_dump(mode="json"),
                    }
                )
            )
        if self.host:
            asyncio.create_task(
                self.host.send_json(
                    {
                        "type": OutboundMessageTypes.PARTICIPANT_CONNECTED,
                        "payload": payload.model_dump(mode="json"),
                    }
                )
            )

    async def participant_disconnected(
        self, payload: ParticipantDisconnectedPayload
    ) -> None:
        """Remove a disconnected participant from the meeting"""
        existing = self.participants.get(payload.id, None)
        if existing is None:
            return
        existing.participant.connected = False
        existing.ws = None
        if self.host:
            asyncio.create_task(
                self.host.send_json(
                    {
                        "type": OutboundMessageTypes.PARTICIPANT_DISCONNECTED,
                        "payload": payload.model_dump(mode="json"),
                    }
                )
            )

    async def check_participant_cap(self, p_id: uuid.UUID) -> bool:
        """
        Checks the room to see if there is space for the participant to join

        Returns:
            True if there is space for another participant, else False
        """
        existing = self.participants.get(p_id, None)
        if existing:
            return True
        connected = sum(
            1 for p in self.participants.values() if p.participant.connected
        )
        cap = getattr(self.service, "participant_cap", None)
        if cap is None:
            cap = await self.service.get_meeting_participant_cap()
        return cap > connected

    async def response_received(self, payload: ResponseReceivedPayload) -> None:
        """Register a new response for the current question"""
        participant = self.participants.get(payload.response.participant_id)
        if participant is None:
            return
        if participant.participant.has_answered is True:
            return
        self.service.add_response(response=payload.response)
        participant.participant.has_answered = True
        if self.host:
            asyncio.create_task(
                self.host.send_json(
                    {
                        "type": OutboundMessageTypes.RESPONSE_RECEIVED,
                        "payload": payload.response,
                    }
                )
            )

    async def reveal(self) -> None:
        """Reveal the current responses to all connected participants"""
        current_responses = self.service.get_current_responses()
        payload = RevealMeetingPayload(responses=current_responses)
        await self._broadcast(
            task=_send_message,
            message={"type": OutboundMessageTypes.REVEAL, "payload": payload},
        )

    async def _broadcast(
        self, task: Callable[..., Coroutine[Any, Any, Any]], *args, **kwargs
    ) -> None:
        """
        Broadcast a task to all connected participants.

        Args:
            task: The coroutine task to execute for each participant.
        """
        for p in self.participants.values():
            if p.ws:
                asyncio.create_task(task(p.ws, *args, **kwargs))
        return

    async def _broadcast_one(
        self,
        task: Callable[..., Coroutine[Any, Any, Any]],
        p_id: uuid.UUID,
        *args,
        **kwargs,
    ) -> None:
        """
        Broadcast a task to a specific participant

        Args:
            task: The coroutine task to execute for the participant
            p_id: The participant to broadcast
        """
        participant = self.participants.get(p_id, None)
        if participant is None:
            return
        if participant.ws is None:
            return
        asyncio.create_task(task(participant.ws, *args, **kwargs))


async def _send_close(ws: WebSocket) -> None:
    """Send a WebSocket close frame indicating normal closure due to meeting room inactivity.

    Args:
        ws: The WebSocket connection to close.
    """
    await ws.close(
        code=status.WS_1000_NORMAL_CLOSURE,
        reason="meeting room destroyed after inactivity",
    )


async def _send_message(ws: WebSocket, message: dict) -> None:
    """
    Send a general message over the WebSocket connection.

    Args:
        ws: The WebSocket connection instance.
        message: The message payload to be sent.
    """
    await ws.send_json(data=message)
