from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp.exceptions import ToolError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Meeting, User
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


@pytest_asyncio.fixture
async def verified_user_meetings(
    session: AsyncSession, verified_user: User
) -> list[Meeting]:
    """
    Seeds three meetings owned by ``verified_user`` for list-meetings tests.
    """
    meetings: list[Meeting] = []
    for i in range(3):
        meeting = Meeting(
            user_id=verified_user.id,
            title=f"Meeting {i}",
            room_code=f"1000000{i}",
            duration=30,
            participant_cap=20,
            total_questions=1,
        )
        session.add(meeting)
        meetings.append(meeting)
    await session.commit()
    for meeting in meetings:
        await session.refresh(meeting)
    return meetings


async def test_list_meetings_returns_meetings(
    mcp_client: Client,
    monkeypatch: pytest.MonkeyPatch,
    verified_user: User,
    verified_user_meetings: list[Meeting],
    mock_session_factory: Callable[[], MockSessionContext],
) -> None:
    """
    Tests that list_meetings returns lightweight summaries of the user's meetings.
    """
    monkeypatch.setattr(
        TOKEN_PATH,
        lambda: fake_token(email=verified_user.email, verified=True),
    )
    monkeypatch.setattr(SESSION_LOCAL_PATH, mock_session_factory)

    result = await mcp_client.call_tool(name="list_meetings", arguments={})
    data: dict[str, Any] = result.structured_content

    assert data["total_returned"] == 3
    assert data["has_more"] is False
    assert data["next_offset"] is None

    titles = {m["title"] for m in data["meetings"]}
    assert titles == {"Meeting 0", "Meeting 1", "Meeting 2"}

    for summary in data["meetings"]:
        assert summary["id"]
        assert summary["room_code"] in {"10000000", "10000001", "10000002"}
        assert summary["status"] == "draft"
        assert summary["question_count"] == 1
        assert summary["created_at"]
        assert summary["url"].endswith(f"/meetings/{summary['id']}/host")


async def test_list_meetings_empty(
    mcp_client: Client,
    monkeypatch: pytest.MonkeyPatch,
    verified_user: User,
    mock_session_factory: Callable[[], MockSessionContext],
) -> None:
    """
    Tests that list_meetings returns an empty result for a user with no meetings.
    """
    monkeypatch.setattr(
        TOKEN_PATH,
        lambda: fake_token(email=verified_user.email, verified=True),
    )
    monkeypatch.setattr(SESSION_LOCAL_PATH, mock_session_factory)

    result = await mcp_client.call_tool(name="list_meetings", arguments={})
    data: dict[str, Any] = result.structured_content

    assert data["meetings"] == []
    assert data["total_returned"] == 0
    assert data["has_more"] is False
    assert data["next_offset"] is None


async def test_list_meetings_pagination(
    mcp_client: Client,
    monkeypatch: pytest.MonkeyPatch,
    verified_user: User,
    verified_user_meetings: list[Meeting],
    mock_session_factory: Callable[[], MockSessionContext],
) -> None:
    """
    Tests limit/offset pagination metadata on list_meetings.
    """
    monkeypatch.setattr(
        TOKEN_PATH,
        lambda: fake_token(email=verified_user.email, verified=True),
    )
    monkeypatch.setattr(SESSION_LOCAL_PATH, mock_session_factory)

    first = await mcp_client.call_tool(
        name="list_meetings", arguments={"limit": 2, "offset": 0}
    )
    first_data: dict[str, Any] = first.structured_content
    assert first_data["total_returned"] == 2
    assert first_data["has_more"] is True
    assert first_data["next_offset"] == 2

    second = await mcp_client.call_tool(
        name="list_meetings", arguments={"limit": 2, "offset": 2}
    )
    second_data: dict[str, Any] = second.structured_content
    assert second_data["total_returned"] == 1
    assert second_data["has_more"] is False
    assert second_data["next_offset"] is None


async def test_list_meetings_unverified_client(
    mcp_client: Client,
    monkeypatch: pytest.MonkeyPatch,
    unverified_user: User,
    mock_session_factory: Callable[[], MockSessionContext],
) -> None:
    """
    Tests that an unverified client cannot list meetings.
    """
    monkeypatch.setattr(
        TOKEN_PATH,
        lambda: fake_token(email=unverified_user.email, verified=False),
    )
    monkeypatch.setattr(SESSION_LOCAL_PATH, mock_session_factory)

    with pytest.raises(ToolError):
        await mcp_client.call_tool(name="list_meetings", arguments={})


@pytest.mark.parametrize("limit", [0, 51])
async def test_list_meetings_invalid_limit(
    mcp_client: Client,
    monkeypatch: pytest.MonkeyPatch,
    verified_user: User,
    mock_session_factory: Callable[[], MockSessionContext],
    limit: int,
) -> None:
    """
    Tests that an out-of-range limit is rejected as a validation error.
    """
    monkeypatch.setattr(
        TOKEN_PATH,
        lambda: fake_token(email=verified_user.email, verified=True),
    )
    monkeypatch.setattr(SESSION_LOCAL_PATH, mock_session_factory)

    with pytest.raises(ToolError) as exc:
        await mcp_client.call_tool(name="list_meetings", arguments={"limit": limit})
    assert "validation" in str(exc.value).lower()
