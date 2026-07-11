import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from src.live.managers import LiveManager
from src.live.schemas import WebIn
from src.middleware.jwt import (
    get_current_participant_websocket,
    get_current_user_websocket,
)
from src.types import MEETING_ID

logger = logging.getLogger(__name__)


lock = asyncio.Lock()

websocket_router = APIRouter(prefix="/meetings", tags=["live"])

manager = LiveManager()


@websocket_router.websocket(
    "/{meeting_id}/host/ws", dependencies=[Depends(get_current_user_websocket)]
)
async def host_websocket(websocket: WebSocket, meeting_id: MEETING_ID) -> None:
    connected = await manager.handle_host_connect(
        meeting_id=meeting_id, websocket=websocket, lock=lock
    )
    if not connected:
        return
    try:
        while True:
            data = WebIn.model_validate(await websocket.receive_json())
            await manager.handle_host_message(meeting_id=meeting_id, message=data)
    except WebSocketDisconnect:
        await manager.handle_host_disconnect(meeting_id=meeting_id)
    except json.JSONDecodeError:
        logger.warning(
            "invalid JSON sent to host",
            extra={"meeting_id": meeting_id, "host": websocket.state.user.email},
        )


@websocket_router.websocket(
    "/{meeting_id}/participant/ws",
    dependencies=[Depends(get_current_participant_websocket)],
)
async def participant_websocket(websocket: WebSocket, meeting_id: MEETING_ID) -> None:
    p_id: uuid.UUID = websocket.state.participant_id
    m_id: uuid.UUID = websocket.state.meeting_id
    connected = await manager.handle_participant_initial_connect(
        meeting_id=meeting_id, p_id=p_id, ws=websocket
    )
    if not connected:
        return
    try:
        while True:
            data = WebIn.model_validate(await websocket.receive_json())
            await manager.handle_participant_message(
                meeting_id=m_id, p_id=p_id, ws=websocket, message=data
            )
    except WebSocketDisconnect:
        await manager.handle_participant_disconnect(meeting_id=m_id, p_id=p_id)
    except json.JSONDecodeError:
        logger.warning(
            "invalid JSON sent to participant",
            extra={"meeting_id": meeting_id, "participant_id": p_id},
        )
