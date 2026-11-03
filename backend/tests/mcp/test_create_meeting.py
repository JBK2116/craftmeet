import uuid
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastmcp import Client
from fastmcp.exceptions import ToolError
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import (
    MAX_DESCRIPTION_LENGTH,
    MAX_MEETING_DURATION_MINUTES,
    MAX_PARTICIPANT_CAP,
    MAX_TITLE_LENGTH,
)
from src.meeting.repository import get_meeting_lazy
from src.models import User
from tests.mcp.conftest import MockSessionContext

TOKEN_PATH = "src.mcp.service.get_access_token"  # noqa: S105
SESSION_LOCAL_PATH = "src.mcp.server.AsyncSessionLocal"  # noqa: S105


def fake_token(email: str, verified: bool) -> SimpleNamespace:
    """
    Returns a fake claims object to be used in `get_access_token` calls.
    :param email: The email field value.
    :param verified: The email_verified field value.
    :return:
    """
    out = {"email": email, "email_verified": verified}
    return SimpleNamespace(claims=out)


async def test_tools_count(mcp_client) -> None:
    """
    Tests that the mcp has the correct amount of tools registered.
    """
    list_tools = await mcp_client.list_tools()
    assert len(list_tools) == 1


async def test_create_verified_client(
    mcp_client: Client,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    verified_user: User,
    valid_meeting: dict[str, Any],
    mock_session_factory: Callable[[], MockSessionContext],
) -> None:
    """
    Tests creating a meeting while being registered as a verified user.
    :param mcp_client:
    :param session:
    :param monkeypatch:
    :param verified_user:
    :param valid_meeting:
    :param mock_session_factory:
    """
    monkeypatch.setattr(
        TOKEN_PATH,
        lambda: fake_token(email=verified_user.email, verified=True),
    )

    monkeypatch.setattr(SESSION_LOCAL_PATH, mock_session_factory)

    result = await mcp_client.call_tool(
        name="create_meeting", arguments={"meeting": valid_meeting}
    )
    assert result.data["question_count"] == len(valid_meeting["questions"])
    assert result.data["title"] == valid_meeting["title"]
    assert result.data["meeting_id"] is not None

    meeting_id = parse_meeting_uuid(meeting_id=result.data["meeting_id"])
    if meeting_id is None:
        pytest.fail(
            f"create_meeting mcp tool returned an invalid or missing meeting_id: {result.data['meeting_id']} "
        )
    meeting = await get_meeting_lazy(db=session, m_id=meeting_id)
    if meeting is None:
        pytest.fail(
            f"create_meeting mcp tool failed to create a valid meeting with id: {result.data['meeting_id']}"
        )

    assert meeting.id == meeting_id
    assert meeting.title == valid_meeting["title"]
    assert meeting.description == valid_meeting["description"]


async def test_create_unverified_client(
    mcp_client: Client,
    monkeypatch: MonkeyPatch,
    unverified_user: User,
    mock_session_factory: Callable[[], MockSessionContext],
    valid_meeting: dict,
) -> None:
    """
    Tests creating a meeting without being registered as a verified user.
    """
    monkeypatch.setattr(
        TOKEN_PATH,
        lambda: fake_token(email=unverified_user.email, verified=False),
    )

    monkeypatch.setattr(SESSION_LOCAL_PATH, mock_session_factory)
    with pytest.raises(ToolError):
        _ = await mcp_client.call_tool(
            name="create_meeting", arguments={"meeting": valid_meeting}
        )


@pytest.mark.parametrize(
    "key, invalid_value",
    [
        ("title", ""),
        ("title", "a" * (MAX_TITLE_LENGTH + 1)),
        ("description", ""),
        ("description", "a" * (MAX_DESCRIPTION_LENGTH + 1)),
        ("questions", []),
        ("participant_cap", MAX_PARTICIPANT_CAP + 1),
        ("duration", MAX_MEETING_DURATION_MINUTES + 1),
    ],
)
async def test_create_invalid_meeting(
    mcp_client: Client,
    monkeypatch: MonkeyPatch,
    verified_user: User,
    valid_meeting: dict[str, Any],
    key: str,
    invalid_value: Any,
    mock_session_factory: Callable[[], MockSessionContext],
) -> None:
    """
    Tests creating a meeting with invalid data.
    """

    monkeypatch.setattr(
        TOKEN_PATH,
        lambda: fake_token(email=verified_user.email, verified=True),
    )

    monkeypatch.setattr(SESSION_LOCAL_PATH, mock_session_factory)

    valid_meeting[key] = invalid_value

    with pytest.raises(ToolError) as exc:
        _ = await mcp_client.call_tool(
            name="create_meeting", arguments={"meeting": valid_meeting}
        )

    assert "validation" in str(exc.value).lower()


def parse_meeting_uuid(meeting_id: str) -> uuid.UUID | None:
    """
    Tries to parse a meetings uuid from string type.
    :param meeting_id: Meeting uuid to parse.
    :return: UUID if valid else None
    """
    try:
        return uuid.UUID(meeting_id)
    except Exception:
        return None
