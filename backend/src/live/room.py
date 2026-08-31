import asyncio
import logging
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import WebSocket, status

from src.live.schemas import (
    AddQuestionFailed,
    AddQuestionPayload,
    AddQuestionSuccessPayload,
    ChatMessage,
    ChatReceivedPayload,
    ChatStatePayload,
    CurrentQuestionPayload,
    GetSnapshotPayload,
    GetSnapshotSuccessPayload,
    KickParticipantPayload,
    KickParticipantResultPayload,
    MeetingStartedPayload,
    MeetingStatePayload,
    NextQuestionPayload,
    Participant,
    ParticipantConnectedPayload,
    ParticipantDisconnectedPayload,
    ParticipantEntry,
    ParticipantJoinRoomFailed,
    ParticipantJoinRoomPayload,
    ParticipantJoinRoomSuccess,
    ParticipantsStatePayload,
    ResponseReceivedPayload,
    RevealMeetingPayload,
)
from src.live.service import LiveService
from src.live.types import CloseCode, OutboundMessageTypes
from src.meeting.schemas import QuestionOut
from src.utils import set_timeout

logger = logging.getLogger(__name__)


class LiveRoom:
    def __init__(
        self,
        room_id: uuid.UUID,
        host: WebSocket,
        on_destroy: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ):
        self.room_id = (
            room_id  # Unique identifier for the room equivalent to meeting id
        )
        self.host: WebSocket | None = (
            host  # host websocket connection, becomes None on disconnects/connection drops
        )
        self.participants: dict[
            uuid.UUID, ParticipantEntry
        ] = {}  # all connected participants
        self.blocked_participants: set[uuid.UUID] = (
            set()
        )  # id of all blocked participants
        self.chat: list[ChatMessage] = []  # list of all chat messages
        self.service = LiveService(
            host_id=host.state.user.id, meeting_id=room_id
        )  # service layer for business logic
        self.meeting_timer: asyncio.Task | None = (
            None  # timer to auto terminate meeting
        )
        self._on_destroy = on_destroy
        self._ended = False
        self._revealed = (
            False  # whether the current question's responses have been revealed
        )

    async def reconnect_host(self, ws: WebSocket) -> None:
        """Reconnect the host to the current meeting"""
        self.host = ws
        logger.debug(
            "host reconnected to room",
            extra={"room_id": str(self.room_id), "host": ws.state.user.email},
        )
        m_state = MeetingStatePayload(
            question=self.service.current_question,
            responses=self.service.get_current_responses(),
            participants=[p.participant for p in self.participants.values()],
            started_at=self.service.get_started_at_time(),
        )
        if len(self.chat) > 0:
            await self.host.send_json(
                data={
                    "type": OutboundMessageTypes.CHAT_STATE,
                    "payload": ChatStatePayload(chats=self.chat).model_dump(
                        mode="json"
                    ),
                }
            )
        await self.host.send_json(
            data={
                "type": OutboundMessageTypes.MEETING_STATE,
                "payload": m_state.model_dump(mode="json"),
            }
        )
        await self._broadcast(
            task=_send_message, message={"type": OutboundMessageTypes.HOST_RECONNECTED}
        )

    async def host_disconnected(self):
        """Send the host disconnected signal to all connected participants"""
        logger.debug(
            "host disconnected from room",
            extra={"room_id": str(self.room_id)},
        )
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
        self.service.add_asked_question(question=payload.question)
        self._revealed = False
        await self.service.start_meeting()
        await self.start_meeting_timer()
        logger.debug(
            "meeting started in room",
            extra={
                "room_id": str(self.room_id),
                "question_id": str(payload.question.id),
            },
        )
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
        self.service.add_asked_question(question=payload.question)
        self._revealed = False
        for p in self.participants.values():
            p.participant.has_answered = False
        logger.debug(
            "advanced to next question",
            extra={
                "room_id": str(self.room_id),
                "question_id": str(payload.question.id),
            },
        )
        await self._broadcast(
            task=_send_message,
            message={
                "type": OutboundMessageTypes.NEXT_QUESTION,
                "payload": payload.model_dump(mode="json"),
            },
        )

    async def add_question(self, payload: AddQuestionPayload) -> None:
        """Adds a new question to the live meeting"""
        result = await self.service.add_question(payload=payload)
        if isinstance(result, QuestionOut):
            out = AddQuestionSuccessPayload(question=result)
            if self.host:
                await self.host.send_json(
                    data={
                        "type": OutboundMessageTypes.ADD_QUESTION_SUCCESS,
                        "payload": out.model_dump(mode="json"),
                    }
                )
        else:
            out = AddQuestionFailed(detail=result)
            if self.host:
                await self.host.send_json(
                    {
                        "type": OutboundMessageTypes.ADD_QUESTION_FAILED,
                        "payload": out.model_dump(mode="json"),
                    }
                )
        return

    async def get_snapshot(self, payload: GetSnapshotPayload) -> None:
        """Get an AI snapshot of the current meeting."""
        response = await self.service.get_snapshot(
            payload=payload,
            participants=list(self.participants.values()),
            chats=self.chat,
        )
        if self.host:
            if isinstance(response, GetSnapshotSuccessPayload):
                await self.host.send_json(
                    {
                        "type": OutboundMessageTypes.GET_SNAPSHOT_SUCCESS,
                        "payload": response.model_dump(mode="json"),
                    }
                )
            else:
                await self.host.send_json(
                    {
                        "type": OutboundMessageTypes.GET_SNAPSHOT_FAILED,
                        "payload": response.model_dump(mode="json"),
                    }
                )
        return

    async def end_stale_meeting(self) -> None:
        """End a stale meeting and close all connected participant websockets."""
        if self.meeting_timer is not None:
            self.meeting_timer.cancel()
        await self.service.end_stale_meeting()
        logger.debug(
            "stale meeting ended in room",
            extra={"room_id": str(self.room_id)},
        )
        await self._broadcast(
            task=_send_message, message={"type": OutboundMessageTypes.MEETING_ENDED}
        )

    async def end_meeting(self) -> None:
        """End a meeting and close all connected participant websockets"""
        if self._ended:
            return
        self._ended = True
        if (
            self.meeting_timer is not None
            and self.meeting_timer is not asyncio.current_task()
        ):
            self.meeting_timer.cancel()
        await self.service.end_meeting(total_participants=len(self.participants))
        logger.debug(
            "meeting ended in room",
            extra={"room_id": str(self.room_id)},
        )
        await self._broadcast(
            task=_send_message, message={"type": OutboundMessageTypes.MEETING_ENDED}
        )
        if self.host:
            asyncio.create_task(
                self.host.send_json({"type": OutboundMessageTypes.MEETING_ENDED})
            )
        if self._on_destroy:
            await self._on_destroy()

    async def handle_sigterm_signal(self) -> None:
        """
        Handles the SIGTERM signal by ending the meeting and closing all
        websockets for both host and participants.
        """
        await self.service.handle_sigterm_signal()
        # Notify the host that the meeting ended
        if self.host:
            asyncio.create_task(
                self.host.close(
                    code=CloseCode.SIGTERM_SIGNAL.code,
                    reason=CloseCode.SIGTERM_SIGNAL.message,
                ),
            )
        # Notify the participants that the meeting has ended
        sockets = [*(p.ws for p in self.participants.values() if p.ws)]
        await asyncio.gather(
            *(
                s.close(
                    code=CloseCode.SIGTERM_SIGNAL.code,
                    reason=CloseCode.SIGTERM_SIGNAL.message,
                )
                for s in sockets
            ),
            return_exceptions=True,
        )

    async def participant_connected(
        self, payload: ParticipantConnectedPayload, p_id: uuid.UUID, ws: WebSocket
    ) -> None:
        """Add a connected participant to the meeting"""
        existing = self.participants.get(p_id, None)
        if existing:
            old_ws = existing.ws
            existing.participant.connected = True
            existing.ws = ws
            logger.debug(
                "participant reconnected to meeting",
                extra={
                    "room_id": str(self.room_id),
                    "participant_id": str(p_id),
                },
            )
            if old_ws and old_ws is not ws:
                try:
                    await old_ws.close(
                        code=CloseCode.PARTICIPANT_RECONNECTED_ELSEWHERE.code,
                        reason=CloseCode.PARTICIPANT_RECONNECTED_ELSEWHERE.message,
                    )
                except RuntimeError:
                    pass

        else:
            new_participant = Participant(
                id=p_id,
                username=None,
                connected=True,
                has_answered=False,
                is_lobby=True,
            )
            self.participants[p_id] = ParticipantEntry(
                participant=new_participant, ws=ws
            )
            logger.debug(
                "participant connected to meeting",
                extra={
                    "room_id": str(self.room_id),
                    "participant_id": str(p_id),
                },
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
        # Replaying/rejoining after the host already revealed: push the reveal
        # snapshot so they aren't left with a blank result view.
        if self._revealed and self.service.current_question is not None:
            asyncio.create_task(
                ws.send_json(
                    {
                        "type": OutboundMessageTypes.REVEAL,
                        "payload": RevealMeetingPayload(
                            responses=self.service.get_current_responses()
                        ).model_dump(mode="json"),
                    }
                )
            )
        if len(self.participants) > 0:
            asyncio.create_task(
                ws.send_json(
                    {
                        "type": OutboundMessageTypes.PARTICIPANTS_STATE,
                        "payload": ParticipantsStatePayload(
                            participants=[
                                entry.participant
                                for entry in self.participants.values()
                            ]
                        ).model_dump(mode="json"),
                    }
                )
            )
        if len(self.chat) > 0:
            await ws.send_json(
                {
                    "type": OutboundMessageTypes.CHAT_STATE,
                    "payload": ChatStatePayload(chats=self.chat).model_dump(
                        mode="json"
                    ),
                }
            )
        if self.host:
            asyncio.create_task(
                self.host.send_json(
                    {
                        "type": OutboundMessageTypes.PARTICIPANT_CONNECTED,
                        "payload": self.participants[p_id].participant.model_dump(
                            mode="json"
                        ),
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
        logger.debug(
            "participant disconnected from room",
            extra={
                "room_id": str(self.room_id),
                "participant_id": str(payload.id),
            },
        )
        if self.host:
            asyncio.create_task(
                self.host.send_json(
                    {
                        "type": OutboundMessageTypes.PARTICIPANT_DISCONNECTED,
                        "payload": payload.model_dump(mode="json"),
                    }
                )
            )

    async def participant_join_room(
        self, p_id: uuid.UUID, ws: WebSocket, payload: ParticipantJoinRoomPayload
    ) -> None:
        """Add a participant to a live meeting room."""
        existing = self.participants.get(p_id)
        if existing is None:
            out = ParticipantJoinRoomFailed(
                detail="Unable to join meeting, please restart the join meeting process"
            )
            await ws.send_json(
                {
                    "type": OutboundMessageTypes.PARTICIPANT_JOIN_ROOM_FAILED,
                    "payload": out.model_dump(mode="json"),
                }
            )
            return
        if self.name_exists(payload.username, exclude_id=p_id):
            out = ParticipantJoinRoomFailed(
                detail="A participant already exists with that username"
            )
            await ws.send_json(
                {
                    "type": OutboundMessageTypes.PARTICIPANT_JOIN_ROOM_FAILED,
                    "payload": out.model_dump(mode="json"),
                }
            )
            return
        existing.participant.username = payload.username
        existing.participant.is_lobby = False
        out = ParticipantJoinRoomSuccess(participant=existing.participant)
        await ws.send_json(
            {
                "type": OutboundMessageTypes.PARTICIPANT_JOIN_ROOM_SUCCESS,
                "payload": out.model_dump(mode="json"),
            }
        )
        if self.host:
            await self.host.send_json(
                {
                    "type": OutboundMessageTypes.PARTICIPANT_CONNECTED,
                    "payload": existing.participant.model_dump(mode="json"),
                }
            )
        await self._broadcast(
            task=_send_message,
            message={
                "type": OutboundMessageTypes.PARTICIPANTS_STATE,
                "payload": ParticipantsStatePayload(
                    participants=[
                        entry.participant for entry in self.participants.values()
                    ]
                ).model_dump(mode="json"),
            },
        )
        return

    async def check_participant_cap(self, p_id: uuid.UUID) -> bool:
        """
        Checks the room to see if there is space for the participant to join

        Returns:
            True if there is space for another participant, else False
        """
        existing = self.participants.get(p_id, None)
        if existing is not None and (
            existing.participant.connected or existing.participant.username is not None
        ):
            return True
        used = sum(
            1
            for p in self.participants.values()
            if p.participant.connected or p.participant.username is not None
        )
        cap = getattr(self.service, "participant_cap", None)
        if cap is None:
            cap = await self.service.get_meeting_participant_cap()
        return cap > used

    async def kick_participant(self, payload: KickParticipantPayload) -> None:
        """Kicks a participant from the meeting"""
        exists = self.participants.get(payload.id)
        if exists is None:
            logger.debug(
                "kick failed: participant not found in room",
                extra={
                    "room_id": str(self.room_id),
                    "participant_id": str(payload.id),
                },
            )
            if self.host:
                logger.debug(
                    "kick_participant_failed sent to host",
                    extra={
                        "room_id": str(self.room_id),
                        "participant_id": str(payload.id),
                    },
                )
                out = KickParticipantResultPayload(
                    detail="Participant not found. They may have already left the meeting.",
                    kicked=False,
                    id=payload.id,
                )
                await self.host.send_json(
                    {
                        "type": OutboundMessageTypes.KICK_PARTICIPANT_FAILED,
                        "payload": out.model_dump(mode="json"),
                    }
                )
                return
            logger.debug(
                "kick_participant_failed dropped: host not connected",
                extra={
                    "room_id": str(self.room_id),
                    "participant_id": str(payload.id),
                },
            )
            return
        logger.debug(
            "kicking participant from meeting",
            extra={
                "room_id": str(self.room_id),
                "participant_id": str(payload.id),
            },
        )
        self.blocked_participants.add(exists.participant.id)
        self.participants.pop(exists.participant.id)
        if exists.ws:
            try:
                await exists.ws.close(
                    code=CloseCode.PARTICIPANT_KICKED_FROM_MEETING.code,
                    reason="You have been kicked from the meeting.",
                )
            except RuntimeError:
                logger.info(
                    "Runtime error occurred when kicking participant from meeting",
                    extra={
                        "room_id": str(self.room_id),
                        "participant_id": str(exists.participant.id),
                    },
                )
                pass
        await self._broadcast(
            task=_send_message,
            message={
                "type": OutboundMessageTypes.PARTICIPANTS_STATE,
                "payload": ParticipantsStatePayload(
                    participants=[
                        entry.participant for entry in self.participants.values()
                    ]
                ).model_dump(mode="json"),
            },
        )
        if self.host:
            logger.debug(
                "kick_participant_success sent to host",
                extra={
                    "room_id": str(self.room_id),
                    "participant_id": str(payload.id),
                },
            )
            out = KickParticipantResultPayload(
                detail="The participant has been kicked from the meeting.",
                kicked=True,
                id=payload.id,
            )
            await self.host.send_json(
                {
                    "type": OutboundMessageTypes.KICK_PARTICIPANT_SUCCESS,
                    "payload": out.model_dump(mode="json"),
                }
            )
            return
        return

    def is_participant_blocked(self, p_id: uuid.UUID) -> bool:
        """Checks if a participant with the provided id is blocked from joining the meeting."""
        return p_id in self.blocked_participants

    def name_exists(self, name: str, exclude_id: uuid.UUID | None = None) -> bool:
        """Checks if a participant with the given name already exists"""
        for v in self.participants.values():
            if v.participant.id == exclude_id:
                continue
            if v.participant.username:
                if v.participant.username.lower() == name.lower():
                    return True
        return False

    async def response_received(self, payload: ResponseReceivedPayload) -> None:
        """Register a new response for the current question"""
        participant = self.participants.get(payload.response.participant_id)
        if participant is None:
            return
        if participant.participant.is_lobby:
            return
        if participant.participant.has_answered:
            return
        self.service.add_response(response=payload.response)
        participant.participant.has_answered = True
        logger.debug(
            "response received in room",
            extra={
                "room_id": str(self.room_id),
                "participant_id": str(payload.response.participant_id),
                "question_id": str(payload.response.question_id),
            },
        )
        if self.host:
            asyncio.create_task(
                self.host.send_json(
                    {
                        "type": OutboundMessageTypes.RESPONSE_RECEIVED,
                        "payload": payload.model_dump(mode="json"),
                    }
                )
            )
            logger.debug(
                "response forwarded to host",
                extra={
                    "room_id": str(self.room_id),
                    "participant_id": str(payload.response.participant_id),
                    "question_id": str(payload.response.question_id),
                },
            )

    async def reveal(self) -> None:
        """Reveal the current responses to all connected participants"""
        self._revealed = True
        current_responses = self.service.get_current_responses()
        payload = RevealMeetingPayload(responses=current_responses)
        logger.debug(
            "responses revealed to participants",
            extra={
                "room_id": str(self.room_id),
                "response_count": len(current_responses),
            },
        )
        await self._broadcast(
            task=_send_message,
            message={
                "type": OutboundMessageTypes.REVEAL,
                "payload": payload.model_dump(mode="json"),
            },
        )

    async def chat_received(self, payload: ChatReceivedPayload) -> None:
        """Register the received chat and broadcast it to everyone else"""
        chat = payload.chat
        if not chat.is_host:
            sender = self.participants.get(chat.u_id)
            if sender is not None and sender.participant.is_lobby:
                return
        self.chat.append(chat)
        if self.host is not None:
            asyncio.create_task(
                self.host.send_json(
                    data={
                        "type": OutboundMessageTypes.CHAT_RECEIVED,
                        "payload": ChatReceivedPayload(chat=payload.chat).model_dump(
                            mode="json"
                        ),
                    }
                )
            )
        for _, p in self.participants.items():
            if p.ws:
                asyncio.create_task(
                    p.ws.send_json(
                        data={
                            "type": OutboundMessageTypes.CHAT_RECEIVED,
                            "payload": ChatReceivedPayload(
                                chat=payload.chat
                            ).model_dump(mode="json"),
                        }
                    )
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
