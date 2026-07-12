from typing import Any

from httpx import AsyncClient

from src.meeting.schemas import JoinMeetingResponse
from src.models import Meeting
from src.utils import generate_participants_meeting_access_token_key

JOIN_URL = "/meetings/join"


async def test_join_meeting_success_draft(
    client: AsyncClient,
    join_meeting_payload: dict[str, Any],
    verified_user_meeting: Meeting,
) -> None:
    """Valid payload for a DRAFT meeting -> 200, returns meeting_id and sets cookie."""
    response = await client.post(JOIN_URL, json=join_meeting_payload)
    assert response.status_code == 200

    body = response.json()
    join_response = JoinMeetingResponse.model_validate(body)
    assert join_response.meeting_id == verified_user_meeting.id

    cookie_key = generate_participants_meeting_access_token_key(
        m_id=str(verified_user_meeting.id)
    )
    assert cookie_key in response.cookies


async def test_join_meeting_success_live(
    client: AsyncClient,
    join_meeting_payload_live: dict[str, Any],
    live_meeting: Meeting,
) -> None:
    """Valid payload for a LIVE meeting -> 200, returns meeting_id and sets cookie."""
    response = await client.post(JOIN_URL, json=join_meeting_payload_live)
    assert response.status_code == 200

    body = response.json()
    join_response = JoinMeetingResponse.model_validate(body)
    assert join_response.meeting_id == live_meeting.id

    cookie_key = generate_participants_meeting_access_token_key(
        m_id=str(live_meeting.id)
    )
    assert cookie_key in response.cookies


async def test_join_meeting_not_found(
    client: AsyncClient,
    join_meeting_payload_nonexistent: dict[str, Any],
) -> None:
    """Room code not in database -> 404."""
    response = await client.post(JOIN_URL, json=join_meeting_payload_nonexistent)
    assert response.status_code == 404


async def test_join_meeting_not_live(
    client: AsyncClient,
    join_meeting_payload_completed: dict[str, Any],
) -> None:
    """Room code for a COMPLETED meeting -> 400."""
    response = await client.post(JOIN_URL, json=join_meeting_payload_completed)
    assert response.status_code == 400
    assert response.json() == "meeting is not live"


async def test_join_meeting_short_username(
    client: AsyncClient,
    verified_user_meeting: Meeting,
) -> None:
    """Username shorter than 3 characters -> 422."""
    payload = {"username": "ab", "code": verified_user_meeting.room_code}
    response = await client.post(JOIN_URL, json=payload)
    assert response.status_code == 422


async def test_join_meeting_long_username(
    client: AsyncClient,
    verified_user_meeting: Meeting,
) -> None:
    """Username longer than 30 characters -> 422."""
    payload = {"username": "a" * 31, "code": verified_user_meeting.room_code}
    response = await client.post(JOIN_URL, json=payload)
    assert response.status_code == 422


async def test_join_meeting_short_code(
    client: AsyncClient,
) -> None:
    """Room code shorter than 8 characters -> 422."""
    payload = {"username": "testuser", "code": "SHORT"}
    response = await client.post(JOIN_URL, json=payload)
    assert response.status_code == 422


async def test_join_meeting_long_code(
    client: AsyncClient,
) -> None:
    """Room code longer than 8 characters -> 422."""
    payload = {"username": "testuser", "code": "TOOLONGCD"}
    response = await client.post(JOIN_URL, json=payload)
    assert response.status_code == 422
