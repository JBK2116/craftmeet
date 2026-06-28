from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.meeting.repository import get_meeting
from src.models import Meeting

EDIT_URL = "/meetings/"  # append the id to this


async def test_edit_meeting_missing_access_token(
    client: AsyncClient,
    session: AsyncSession,
    verified_user_meeting: Meeting,
    update_meeting_payload: dict[str, Any],
) -> None:
    url = EDIT_URL + str(verified_user_meeting.id)
    m_id = verified_user_meeting.id
    updated_at = verified_user_meeting.updated_at

    response = await client.patch(url=url, json=update_meeting_payload)
    assert response.status_code == 401

    meeting = await get_meeting(db=session, m_id=m_id)
    assert meeting is not None
    assert meeting.updated_at == updated_at  # meeting was not altered


async def test_edit_meeting_expired_access_token(
    client: AsyncClient,
    session: AsyncSession,
    expired_access_token_jwt: str,
    verified_user_meeting: Meeting,
    update_meeting_payload: dict[str, Any],
) -> None:
    url = EDIT_URL + str(verified_user_meeting.id)
    m_id = verified_user_meeting.id
    updated_at = verified_user_meeting.updated_at

    client.cookies.set("access_token", expired_access_token_jwt)

    response = await client.patch(url=url, json=update_meeting_payload)
    assert response.status_code == 401

    meeting = await get_meeting(db=session, m_id=m_id)
    assert meeting is not None
    assert meeting.updated_at == updated_at  # meeting was not altered


async def test_edit_meeting_invalid_access_token(
    client: AsyncClient,
    session: AsyncSession,
    verified_user_meeting: Meeting,
    update_meeting_payload: dict[str, Any],
) -> None:
    url = EDIT_URL + str(verified_user_meeting.id)
    m_id = verified_user_meeting.id
    updated_at = verified_user_meeting.updated_at

    client.cookies.set("access_token", "skdjfnkjdsnfkjsndfkjns")

    response = await client.patch(url=url, json=update_meeting_payload)
    assert response.status_code == 401

    meeting = await get_meeting(db=session, m_id=m_id)
    assert meeting is not None
    assert meeting.updated_at == updated_at  # meeting was not altered


async def test_edit_meeting_orphan_access_token(
    client: AsyncClient,
    session: AsyncSession,
    verified_user_meeting: Meeting,
    update_meeting_payload: dict[str, Any],
    orphan_access_token_jwt: str,
) -> None:
    url = EDIT_URL + str(verified_user_meeting.id)
    m_id = verified_user_meeting.id
    updated_at = verified_user_meeting.updated_at

    client.cookies.set("access_token", orphan_access_token_jwt)

    response = await client.patch(url=url, json=update_meeting_payload)
    assert response.status_code == 401

    meeting = await get_meeting(db=session, m_id=m_id)
    assert meeting is not None
    assert meeting.updated_at == updated_at  # meeting was not altered


async def test_edit_meeting_cross_ownership(
    authenticated_client: AsyncClient,
    another_user_meeting: Meeting,
    update_meeting_payload: dict[str, Any],
) -> None:
    url = EDIT_URL + str(another_user_meeting.id)
    # authenticated_client here logs in with verified_user
    response = await authenticated_client.patch(url, json=update_meeting_payload)
    assert response.status_code == 401
