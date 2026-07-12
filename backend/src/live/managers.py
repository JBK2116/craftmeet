import asyncio
import logging
import uuid

from fastapi import WebSocket, status

from src.live.room import LiveRoom
from src.live.schemas import (
    ParticipantConnectedPayload,
    ParticipantDisconnectedPayload,
    WebIn,
)
from src.live.types import CloseCode, InboundMessageTypes
from src.utils import set_timeout

logger = logging.getLogger(__name__)


class LiveManager:
    STALE_TIMEOUT_SECONDS = 60 * 5

    def __init__(self):
        self.__rooms: dict[uuid.UUID, LiveRoom] = {}
        self.__destroy_tasks: dict[uuid.UUID, asyncio.Task] = {}

    async def handle_host_message(self, meeting_id: uuid.UUID, message: WebIn):
        """
        Handle an incoming WebSocket host message for a given meeting.

        Dispatches the message to the appropriate room method based on the
        message type.  If the meeting room does not exist, the message is
        silently ignored.

        Args:
            meeting_id: Unique identifier of the meeting.
            message: The incoming WebSocket message with its type and payload.
        """
        room = self.__rooms.get(meeting_id, None)
        if room is None:
            return
        match message.type:
            case InboundMessageTypes.MEETING_STARTED:
                await room.start_meeting(payload=message.payload)
            case InboundMessageTypes.MEETING_ENDED:
                await room.end_meeting()
                await self.__destroy_room(meeting_id)
            case InboundMessageTypes.NEXT_QUESTION:
                await room.next_question(payload=message.payload)
            case InboundMessageTypes.REVEAL:
                await room.reveal()

    async def handle_participant_message(
        self, meeting_id: uuid.UUID, p_id: uuid.UUID, ws: WebSocket, message: WebIn
    ) -> None:
        match message.type:
            case InboundMessageTypes.PARTICIPANT_CONNECTED:
                await self.handle_participant_full_connect(
                    meeting_id=meeting_id, p_id=p_id, payload=message.payload, ws=ws
                )
            case InboundMessageTypes.RESPONSE_RECEIVED:
                room = self.__rooms.get(meeting_id, None)
                if room is None:
                    return
                await room.response_received(payload=message.payload)

    async def handle_host_connect(
        self, meeting_id: uuid.UUID, websocket: WebSocket, lock: asyncio.Lock
    ) -> bool:
        """
        Accept a host WebSocket connection for a meeting, ensuring that a new host cannot
        connect to a currently live meeting whilst the old host is still connected.

        Args:
            meeting_id: The meeting the host is joining.
            websocket: The host's WebSocket connection.
            lock: An asyncio.Lock to serialize access to active_connections.

        Returns:
            True if the connection was accepted, False if it was rejected.
        """
        async with lock:
            await websocket.accept()
            logger.debug(
                "host websocket attempting to connect",
                extra={"host": websocket.state.user.email, "meeting_id": meeting_id},
            )
            task = self.__destroy_tasks.get(meeting_id, None)
            if task is not None:
                task.cancel()
                logger.debug(
                    "cancelled destroy live meeting task", extra={"type": "destroy"}
                )

            existing_room = self.__rooms.get(meeting_id, None)
            if existing_room is None:

                async def _destroy_room():
                    await self.__destroy_room(meeting_id)

                self.__rooms[meeting_id] = LiveRoom(
                    room_id=meeting_id, host=websocket, on_destroy=_destroy_room
                )
                await self.__rooms[meeting_id].service.host_connected()
                logger.debug(
                    "host websocket connected to new meeting room",
                    extra={
                        "room_id": str(meeting_id),
                        "host": websocket.state.user.email,
                    },
                )
                return True
            else:
                if existing_room.host is None:
                    await existing_room.reconnect_host(ws=websocket)
                    logger.debug(
                        "host reconnected to existing meeting room",
                        extra={
                            "room_id": str(meeting_id),
                            "host": websocket.state.user.email,
                        },
                    )
                    return True
                # verify that the existing host is still properly connected
                try:
                    await existing_room.host.send_json({"type": "__host_verify"})
                except Exception:
                    # stale host connection
                    logger.debug(
                        "existing host WebSocket is stale, allowing new host",
                        extra={"room_id": str(meeting_id)},
                    )
                    existing_room.host = None
                    await existing_room.reconnect_host(ws=websocket)
                    logger.debug(
                        "host reconnected (stale host cleared)",
                        extra={
                            "room_id": str(meeting_id),
                            "host": websocket.state.user.email,
                        },
                    )
                    return True
                # host is still connected so fully reject this connection request
                await websocket.close(
                    code=CloseCode.HOST_ALREADY_CONNECTED.code,
                    reason=CloseCode.HOST_ALREADY_CONNECTED.message,
                )
                logger.debug(
                    "host rejected from connecting to meeting room",
                    extra={
                        "room_id": str(meeting_id),
                        "host": websocket.state.user.email,
                    },
                )
                return False

    async def handle_host_disconnect(self, meeting_id: uuid.UUID) -> None:
        """
        Handles the disconnection of a host from a meeting room.

        When a host disconnects, this method logs the event, checks if the
        meeting room exists, and schedules a cleanup task that will destroy
        the room if it remains stale for a defined timeout period.

        Args:
            meeting_id: The UUID of the meeting room from which the host disconnected.
        """
        logger.debug(
            "host disconnected from meeting room", extra={"room_id": str(meeting_id)}
        )
        room = self.__rooms.get(meeting_id, None)
        if room is None:
            (
                logger.debug(
                    "no meeting room found", extra={"meeting_id": str(meeting_id)}
                ),
            )
            return
        room.host = None
        task = set_timeout(
            callback=self.__destroy_if_stale,
            delay_seconds=self.STALE_TIMEOUT_SECONDS,
            meeting_id=meeting_id,
        )
        self.__destroy_tasks[meeting_id] = task
        logger.debug(
            "destroy task created for meeting room",
            extra={
                "task_timeout_minutes": self.STALE_TIMEOUT_SECONDS // 60,
                "meeting_id": str(meeting_id),
            },
        )
        await room.host_disconnected()

    async def handle_participant_initial_connect(
        self, meeting_id: uuid.UUID, p_id: uuid.UUID, ws: WebSocket
    ) -> bool:
        """
        Accept a participant's initial websocket request if the meeting is still live.

        Args:
            meeting_id: The UUID of the meeting.
            p_id: The UUID of the participant.
            ws: The WebSocket connection to accept.

        Returns:
            True if the websocket was accepted, False if the meeting was not found.
        """
        logger.debug(
            "participant websocket attempting to connect",
            extra={"meeting_id": str(meeting_id), "participant_id": str(p_id)},
        )
        room = self.__rooms.get(meeting_id, None)
        if room is None:
            logger.debug(
                "no meeting room found for participant",
                extra={"meeting_id": str(meeting_id), "participant_id": str(p_id)},
            )
            return False
        has_space = await room.check_participant_cap(p_id=p_id)
        if not has_space:
            return False
        await ws.accept()
        return True

    async def handle_participant_full_connect(
        self,
        meeting_id: uuid.UUID,
        p_id: uuid.UUID,
        payload: ParticipantConnectedPayload,
        ws: WebSocket,
    ) -> None:
        """
        Handle a participant's full connection to a meeting.

        This method validates that the meeting room exists, logs connection
        attempts, and either closes the WebSocket if the room is missing or
        registers the participant in the room.

        Args:
            meeting_id: UUID of the meeting the participant is joining.
            p_id: UUID of the participant attempting to connect.
            payload: ParticipantConnectedPayload with connection details
                     (e.g., username).
            ws: WebSocket connection to accept.
        """
        logger.debug(
            "participant attempting to join meeting",
            extra={
                "meeting_id": meeting_id,
                "participant_id": p_id,
                "username": payload.username,
            },
        )
        room = self.__rooms.get(meeting_id, None)
        if room is None:
            logger.debug(
                "no meeting room found for participant",
                extra={
                    "meeting_id": str(meeting_id),
                    "participant_id": str(p_id),
                    "username": payload.username,
                },
            )
            await ws.close(
                code=status.WS_1000_NORMAL_CLOSURE,
                reason="meeting room not found or ended",
            )
            return
        await room.participant_connected(payload=payload, p_id=p_id, ws=ws)

    async def handle_participant_disconnect(
        self, meeting_id: uuid.UUID, p_id: uuid.UUID
    ) -> None:
        """Handle a participant disconnecting from a meeting.

        Args:
            meeting_id: The UUID of the meeting.
            p_id: The UUID of the participant who disconnected.
        """
        logger.debug(
            "participant disconnected from meeting",
            extra={"meeting_id": str(meeting_id)},
        )
        room = self.__rooms.get(meeting_id, None)
        if room is None:
            return
        payload = ParticipantDisconnectedPayload(id=p_id)
        await room.participant_disconnected(payload=payload)

    async def __destroy_if_stale(self, meeting_id: uuid.UUID) -> None:
        """
        Destroy a meeting room if it is considered stale.

        A room is considered stale if it exists and no longer has a host connected.
        This method checks the current room state and destroys it if appropriate.

        Args:
            meeting_id: The UUID of the meeting room to check.
        """
        room = self.__rooms.get(meeting_id, None)
        if room is None or room.host:
            logger.debug(
                "no meeting room destroyed",
                extra={
                    "reason": "room not found or host still connected",
                    "room_id": str(meeting_id),
                },
            )
            return
        await room.end_stale_meeting()
        await self.__destroy_room(meeting_id=meeting_id)

    async def __destroy_room(self, meeting_id: uuid.UUID) -> None:
        """
        Destroy a live meeting room asynchronously.

        Args:
            meeting_id: The UUID of the meeting room to destroy.
        """
        self.__rooms.pop(meeting_id, None)
        logger.debug("meeting room destroyed", {"room_id": str(meeting_id)})
        task = self.__destroy_tasks.pop(meeting_id, None)
        if task is not None:
            task.cancel()
            logger.debug(
                "destroy room task cancelled", extra={"meeting_id": meeting_id}
            )
