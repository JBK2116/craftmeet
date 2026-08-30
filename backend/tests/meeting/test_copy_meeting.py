import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Meeting

COPY_URL = "/meetings/"  # append the {id}/copy to this


async def test_copy_meeting_invalid_token(
    session: AsyncSession,
    client: AsyncClient,
    copy_meeting_payload: dict[str, Any],
    verified_user_meeting: Meeting,
) -> None:
    """Malformed access token -> 401, meeting not copied."""
    url = COPY_URL + str(verified_user_meeting.id) + "/copy"

    response = await client.post(url, json=copy_meeting_payload)
    assert response.status_code == 401

    meeting = await _find_copy(session=session, title=copy_meeting_payload["title"])
    assert meeting is None


async def test_copy_meeting_expired_token(
    session: AsyncSession,
    client: AsyncClient,
    verified_user_meeting: Meeting,
    copy_meeting_payload: dict[str, Any],
    expired_access_token_jwt: str,
) -> None:
    """Expired access token -> 401, meeting not copied."""
    url = COPY_URL + str(verified_user_meeting.id) + "/copy"

    client.cookies.set("access_token", expired_access_token_jwt)

    response = await client.post(url=url, json=copy_meeting_payload)
    assert response.status_code == 401

    meeting = await _find_copy(session=session, title=copy_meeting_payload["title"])
    assert meeting is None


async def test_copy_meeting_missing_access_token(
    session: AsyncSession,
    client: AsyncClient,
    verified_user_meeting: Meeting,
    copy_meeting_payload: dict[str, Any],
) -> None:
    """Missing access token -> 401, meeting not copied."""
    url = COPY_URL + str(verified_user_meeting.id) + "/copy"

    response = await client.post(url=url, json=copy_meeting_payload)
    assert response.status_code == 401

    meeting = await _find_copy(session=session, title=copy_meeting_payload["title"])
    assert meeting is None


async def test_copy_meeting_orphan_access_token(
    session: AsyncSession,
    client: AsyncClient,
    verified_user_meeting: Meeting,
    copy_meeting_payload: dict[str, Any],
    orphan_access_token_jwt: str,
) -> None:
    """Orphan access token -> 401, meeting not copied."""
    url = COPY_URL + str(verified_user_meeting.id) + "/copy"

    client.cookies.set("access_token", orphan_access_token_jwt)

    response = await client.post(url=url, json=copy_meeting_payload)
    assert response.status_code == 401

    meeting = await _find_copy(session=session, title=copy_meeting_payload["title"])
    assert meeting is None


async def test_copy_meeting_orphan_meeting(
    session: AsyncSession,
    authenticated_client: AsyncClient,
    copy_meeting_payload: dict[str, Any],
) -> None:
    """Meeting not found -> 401, meeting not copied."""
    url = COPY_URL + str(uuid.uuid4()) + "/copy"

    response = await authenticated_client.post(url=url, json=copy_meeting_payload)
    assert response.status_code == 404

    meeting = await _find_copy(session=session, title=copy_meeting_payload["title"])
    assert meeting is None

    return


async def test_copy_meeting_success(
    session: AsyncSession,
    authenticated_client: AsyncClient,
    verified_user_meeting: Meeting,
    copy_meeting_payload: dict[str, Any],
) -> None:
    """Meeting is found -> 201, meeting is copied."""
    url = COPY_URL + str(verified_user_meeting.id) + "/copy"

    response = await authenticated_client.post(url=url, json=copy_meeting_payload)
    assert response.status_code == 201

    meeting = await _find_copy(session=session, title=copy_meeting_payload["title"])
    assert meeting is not None

    assert meeting.title == copy_meeting_payload["title"]
    assert meeting.title != verified_user_meeting.title
    assert meeting.participant_cap == verified_user_meeting.participant_cap
    assert meeting.description == verified_user_meeting.description
    # meetings are a structural match with the only the title being different

    return


async def _find_copy(session: AsyncSession, title: str) -> Meeting | None:
    """Queries the database for the copied meeting object."""
    stmt = select(Meeting).where(Meeting.title == title)
    row = await session.execute(stmt)
    meeting = row.scalar_one_or_none()
    return meeting
