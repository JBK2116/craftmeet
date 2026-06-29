from httpx import AsyncClient

from src.meeting.schemas import MeetingOut
from src.models import Meeting, User

GET_URL = "/meetings/"


async def test_get_meeting_missing_access_token(
    client: AsyncClient, verified_user_meeting: Meeting
) -> None:
    """No access token cookie sent -> 401."""
    url = GET_URL + str(verified_user_meeting.id)

    response = await client.get(url=url)
    assert response.status_code == 401


async def test_get_meeting_invalid_access_token(
    client: AsyncClient, verified_user_meeting: Meeting
) -> None:
    """Malformed access token -> 401."""
    url = GET_URL + str(verified_user_meeting.id)

    client.cookies.set("access_token", "sndkjgnqiugoinweogqgenoiq")

    response = await client.get(url=url)
    assert response.status_code == 401


async def test_get_meeting_expired_access_token(
    client: AsyncClient,
    expired_access_token_jwt: str,
    verified_user_meeting: Meeting,
) -> None:
    """Expired access token -> 401."""
    url = GET_URL + str(verified_user_meeting.id)

    client.cookies.set("access_token", expired_access_token_jwt)

    response = await client.get(url=url)
    assert response.status_code == 401


async def test_get_meeting_orphan_access_token(
    client: AsyncClient, orphan_access_token_jwt: str, verified_user_meeting: Meeting
) -> None:
    """Valid JWT for a non-existent user -> 401."""
    url = GET_URL + str(verified_user_meeting.id)

    client.cookies.set("access_token", orphan_access_token_jwt)

    response = await client.get(url=url)
    assert response.status_code == 401


async def test_get_meeting_cross_ownership(
    authenticated_client: AsyncClient,
    another_user_meeting: Meeting,
) -> None:
    """Authenticated user tries to get another user's meeting -> 401."""
    url = GET_URL + str(another_user_meeting.id)

    response = await authenticated_client.get(url)
    assert response.status_code == 401


async def test_get_meeting_valid_access_token(
    authenticated_client: AsyncClient,
    verified_user_meeting: Meeting,
    verified_meeting_user: User,
) -> None:
    """Valid access token, meeting owned by user -> 200, meeting returned with correct user_id."""
    url = GET_URL + str(verified_user_meeting.id)
    user_id = verified_meeting_user.id

    response = await authenticated_client.get(url)
    assert response.status_code == 200

    body = response.json()
    meeting_out = MeetingOut.model_validate(body)
    assert meeting_out.user_id == user_id
