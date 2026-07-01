from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.meeting.repository import get_meeting
from src.models import Meeting, User

DELETES_URL = "/meetings"


async def test_delete_meetings_missing_access_token(client: AsyncClient) -> None:
    """No access token cookie sent -> 401."""
    response = await client.delete(DELETES_URL)
    assert response.status_code == 401


async def test_delete_meetings_invalid_access_token(client: AsyncClient) -> None:
    """Malformed access token -> 401."""
    client.cookies.set("access_token", "bginegiqnroingqeoirgqer")

    response = await client.delete(DELETES_URL)
    assert response.status_code == 401


async def test_delete_meetings_expired_access_token(
    client: AsyncClient, expired_access_token_jwt: str
) -> None:
    """Expired access token -> 401."""
    client.cookies.set("access_token", expired_access_token_jwt)

    response = await client.delete(DELETES_URL)
    assert response.status_code == 401


async def test_delete_meetings_orphan_access_token(
    client: AsyncClient, orphan_access_token_jwt: str
) -> None:
    """Valid JWT for a non-existent user -> 401."""
    client.cookies.set("access_token", orphan_access_token_jwt)

    response = await client.delete(DELETES_URL)
    assert response.status_code == 401


async def test_delete_meetings_cross_ownership(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    another_user_meeting: Meeting,
    another_meeting_user: User,
) -> None:
    """Authenticated user deletes another user's meeting -> 204 (idempotent), meeting unchanged."""
    m_id = another_user_meeting.id
    u_id = another_meeting_user.id

    response = await authenticated_client.delete(DELETES_URL)
    assert response.status_code == 204  # idempotent

    meeting = await get_meeting(db=session, m_id=m_id)
    assert meeting is not None
    assert meeting.id == m_id
    assert meeting.user_id == u_id


async def test_delete_meetings_valid_access_token(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    verified_user_meeting: Meeting,
    second_verified_user_meeting: Meeting,
) -> None:
    """Valid access token, meeting owned by user -> 204, meetings deleted from DB."""
    m_ids = [verified_user_meeting.id, second_verified_user_meeting.id]

    response = await authenticated_client.delete(DELETES_URL)
    assert response.status_code == 204

    for m_id in m_ids:
        meeting = await get_meeting(db=session, m_id=m_id)
        assert meeting is None
