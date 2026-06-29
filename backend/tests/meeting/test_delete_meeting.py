from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.meeting.repository import get_meeting
from src.models import Meeting, User

DELETE_URL = "/meetings/"


async def test_delete_missing_access_token(
    client: AsyncClient,
    session: AsyncSession,
    verified_user_meeting: Meeting,
) -> None:
    """No access token cookie sent -> 401, meeting not deleted."""
    url = DELETE_URL + str(verified_user_meeting.id)
    m_id = verified_user_meeting.id

    response = await client.delete(url)
    assert response.status_code == 401

    meeting = await get_meeting(db=session, m_id=m_id)
    assert meeting is not None


async def test_delete_invalid_access_token(
    client: AsyncClient,
    session: AsyncSession,
    verified_user_meeting: Meeting,
) -> None:
    """Malformed access token -> 401, meeting not deleted."""
    url = DELETE_URL + str(verified_user_meeting.id)
    m_id = verified_user_meeting.id

    client.cookies.set("access_token", "sjdnfkjangkjnawhureiahuwn")
    response = await client.delete(url)
    assert response.status_code == 401

    meeting = await get_meeting(db=session, m_id=m_id)
    assert meeting is not None


async def test_delete_expired_access_token(
    client: AsyncClient,
    session: AsyncSession,
    verified_user_meeting: Meeting,
    expired_access_token_jwt: str,
) -> None:
    """Expired access token -> 401, meeting not deleted."""
    url = DELETE_URL + str(verified_user_meeting.id)
    m_id = verified_user_meeting.id
    client.cookies.set("access_token", expired_access_token_jwt)

    response = await client.delete(url)
    assert response.status_code == 401

    meeting = await get_meeting(db=session, m_id=m_id)
    assert meeting is not None


async def test_delete_orphan_access_token(
    client: AsyncClient,
    session: AsyncSession,
    verified_user_meeting: Meeting,
    orphan_access_token_jwt: str,
) -> None:
    """Valid JWT for a non-existent user -> 401, meeting not deleted."""
    url = DELETE_URL + str(verified_user_meeting.id)
    m_id = verified_user_meeting.id
    client.cookies.set("access_token", orphan_access_token_jwt)

    response = await client.delete(url)
    assert response.status_code == 401

    meeting = await get_meeting(db=session, m_id=m_id)
    assert meeting is not None


async def test_delete_cross_ownership(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    another_user_meeting: Meeting,
    verified_meeting_user: User,
) -> None:
    """Authenticated user tries to delete another user's meeting -> 404, meeting not deleted."""
    url = DELETE_URL + str(another_user_meeting.id)
    m_id = another_user_meeting.id

    response = await authenticated_client.delete(url)
    assert response.status_code == 404

    meeting = await get_meeting(db=session, m_id=m_id)
    assert meeting is not None
    assert meeting.user_id != verified_meeting_user.id


async def test_delete_meeting_valid_access_token(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    verified_user_meeting: Meeting,
) -> None:
    """Valid access token, meeting owned by user -> 204, meeting deleted from DB."""
    url = DELETE_URL + str(verified_user_meeting.id)
    m_id = verified_user_meeting.id

    response = await authenticated_client.delete(url)
    assert response.status_code == 204

    meeting = await get_meeting(db=session, m_id=m_id)
    assert meeting is None
