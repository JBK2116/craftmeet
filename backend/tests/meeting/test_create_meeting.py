from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.meeting.repository import get_meeting
from src.meeting.schemas import MeetingOut
from src.models import User

CREATE_URL = "/meetings"


async def test_create_meeting_missing_access_token(
    client: AsyncClient, create_meeting_payload: dict[str, Any]
) -> None:
    """No access token cookie sent -> 401."""
    response = await client.post(CREATE_URL, json=create_meeting_payload)
    assert response.status_code == 401


async def test_create_meeting_invalid_access_token(
    client: AsyncClient, create_meeting_payload: dict[str, Any]
) -> None:
    """Malformed access token -> 401."""
    client.cookies.set("access_token", "iansgnaosngoasmdkmiqnroignqoirng")
    response = await client.post(CREATE_URL, json=create_meeting_payload)
    assert response.status_code == 401


async def test_create_meeting_expired_access_token(
    client: AsyncClient,
    expired_access_token_jwt: str,
    create_meeting_payload: dict[str, Any],
) -> None:
    """Expired access token -> 401."""
    client.cookies.set("access_token", expired_access_token_jwt)
    response = await client.post(CREATE_URL, json=create_meeting_payload)
    assert response.status_code == 401


async def test_create_meeting_orphan_access_token(
    client: AsyncClient,
    orphan_access_token_jwt: str,
    create_meeting_payload: dict[str, Any],
) -> None:
    """Valid JWT for a non-existent user -> 401."""
    client.cookies.set("access_token", orphan_access_token_jwt)
    response = await client.post(CREATE_URL, json=create_meeting_payload)
    assert response.status_code == 401


async def test_create_meeting_valid_access_token(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    verified_meeting_user: User,
    create_meeting_payload: dict[str, Any],
) -> None:
    """Valid access token, valid payload -> 201, meeting persisted with correct owner."""
    response = await authenticated_client.post(CREATE_URL, json=create_meeting_payload)
    assert response.status_code == 201

    body = response.json()
    meeting_out = MeetingOut.model_validate(body)

    meeting_db = await get_meeting(db=session, m_id=meeting_out.id)
    assert meeting_db is not None
    assert meeting_db.id == meeting_out.id
    assert meeting_db.user_id == verified_meeting_user.id
