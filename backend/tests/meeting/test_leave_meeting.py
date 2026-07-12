from httpx import AsyncClient

from src.models import Meeting
from src.utils import generate_participants_meeting_access_token_key

LEAVE_URL = "/meetings/{meeting_id}/leave"


async def test_leave_meeting_success(
    client: AsyncClient, verified_user_meeting: Meeting
) -> None:
    """Valid meeting ID -> 204, participant cookie is cleared."""
    url = LEAVE_URL.format(meeting_id=str(verified_user_meeting.id))
    response = await client.post(url)
    assert response.status_code == 204

    cookie_key = generate_participants_meeting_access_token_key(
        m_id=str(verified_user_meeting.id)
    )
    set_cookie = response.headers.get("set-cookie", "")
    assert cookie_key in set_cookie
    # max_age=0 means the cookie is immediately expired
    assert "Max-Age=0" in set_cookie


async def test_leave_meeting_invalid_uuid(client: AsyncClient) -> None:
    """Non-UUID meeting_id in path -> 422."""
    url = LEAVE_URL.format(meeting_id="not-a-uuid")
    response = await client.post(url)
    assert response.status_code == 422
