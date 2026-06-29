from httpx import AsyncClient

from src.meeting.schemas import MeetingOut
from src.models import Meeting, User

MEETINGS_URL = "/meetings"


async def test_get_meetings_missing_access_token(client: AsyncClient) -> None:
    """No access token cookie sent -> 401."""
    response = await client.get(MEETINGS_URL)
    assert response.status_code == 401


async def test_get_meetings_invalid_access_token(client: AsyncClient) -> None:
    """Malformed access token -> 401."""
    client.cookies.set("access_token", "sgkqhgrengqreg")

    response = await client.get(MEETINGS_URL)
    assert response.status_code == 401


async def test_get_meetings_orphan_access_token(
    client: AsyncClient, orphan_access_token_jwt: str
) -> None:
    """Valid JWT for a non-existent user -> 401."""
    client.cookies.set("access_token", orphan_access_token_jwt)

    response = await client.get(MEETINGS_URL)
    assert response.status_code == 401


async def test_get_meetings_expired_access_token(
    client: AsyncClient, expired_access_token_jwt: str
) -> None:
    """Expired access token -> 401."""
    client.cookies.set("access_token", expired_access_token_jwt)

    response = await client.get(MEETINGS_URL)
    assert response.status_code == 401


async def test_get_meetings_valid_access_token(
    authenticated_client: AsyncClient,
    verified_meeting_user: User,
    verified_user_meeting: Meeting,
    second_verified_user_meeting: Meeting,
) -> None:
    """Valid access token -> 200, returns the authenticated user's meetings."""
    response = await authenticated_client.get(MEETINGS_URL)
    assert response.status_code == 200

    body = response.json()
    meetings_out = [MeetingOut.model_validate(meeting) for meeting in body]
    for m in meetings_out:
        assert m.user_id == verified_meeting_user.id
        assert (
            m.id == verified_user_meeting.id or m.id == second_verified_user_meeting.id
        )
