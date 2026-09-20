"""Fixtures for the live-module contract tests.

Seams that touch implementation internals are confined to this file, so a
rewrite only has to adapt them here:

* ``src.live.router.manager`` / ``src.live.router.lock``  (fresh per test)
* ``AsyncSessionLocal`` in ``src.live.service`` and ``src.middleware.jwt``
  (``LiveService`` and the JWT dependencies open their own sessions and so
  bypass the ``get_db`` override; they are pointed at the test connection)
* ``src.live.room.set_timeout`` (only for the meeting-duration timer test)
* the stale-host / stale-lobby timeout attributes on the manager
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI, Path, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.websockets import WebSocket as StarletteWebSocket

from src.auth.crypto import hash_password
from src.live import router as live_router
from src.live.managers import LiveManager
from src.middleware.jwt import (
    get_current_participant_websocket,
    get_current_user_websocket,
)
from src.models import Meeting, User
from src.types import MeetingStatus
from src.utils import set_timeout as real_set_timeout
from tests.live.harness import LiveHarness, fake_user

# Effectively disabled unless a test opts in with ``short_timeouts``.
LONG_TIMEOUT = 600.0
SHORT_TIMEOUT = 0.2


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "expects_server_error: tolerate unhandled server-side exceptions that the "
        "current implementation raises (invisible or accepted on the wire); by "
        "default any exception escaping the ASGI app fails the test",
    )


# isolation
@pytest.fixture(autouse=True)
def _live_db(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point every ``AsyncSessionLocal`` used by the live path at the test DB.

    Sessions are bound to the test connection (joined via savepoints, so the
    per-test rollback still applies) and serialised with a lock because they
    all share that single connection.
    """
    maker = async_sessionmaker(
        bind=session.bind,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    gate = asyncio.Lock()

    @asynccontextmanager
    async def factory() -> AsyncGenerator[AsyncSession, None]:
        async with gate:
            async with maker() as db:
                yield db

    monkeypatch.setattr("src.live.service.AsyncSessionLocal", factory)
    monkeypatch.setattr("src.middleware.jwt.AsyncSessionLocal", factory)


@pytest.fixture(autouse=True)
def live_manager(monkeypatch: pytest.MonkeyPatch) -> LiveManager:
    """A fresh manager + lock per test (the router keeps them as globals).

    Stale timeouts default to "never fires"; opt in to ~0.2s with the
    ``short_timeouts`` fixture. (A 0.2s stale-lobby timeout would otherwise
    tear down the room under every ordinary multi-step test.)
    """
    manager = LiveManager()
    manager.STALE_HOST_TIMEOUT_SECONDS = LONG_TIMEOUT
    manager.STALE_LOBBY_TIMEOUT_SECONDS = LONG_TIMEOUT
    monkeypatch.setattr(live_router, "manager", manager)
    monkeypatch.setattr(live_router, "lock", asyncio.Lock())
    return manager


@pytest.fixture
def short_timeouts(live_manager: LiveManager) -> float:
    live_manager.STALE_HOST_TIMEOUT_SECONDS = SHORT_TIMEOUT
    live_manager.STALE_LOBBY_TIMEOUT_SECONDS = SHORT_TIMEOUT
    return SHORT_TIMEOUT


@pytest.fixture
def fast_meeting_timer(monkeypatch: pytest.MonkeyPatch) -> float:
    """Make the meeting-duration timer (minutes in the DB) fire after 0.2s."""

    def fast(callback, delay_seconds, *args, **kwargs):
        return real_set_timeout(callback, SHORT_TIMEOUT, *args, **kwargs)

    monkeypatch.setattr("src.live.room.set_timeout", fast)
    return SHORT_TIMEOUT


# data
@pytest_asyncio.fixture
async def host_user(session: AsyncSession) -> User:
    user = User(
        email=f"h{uuid.uuid4().hex[:10]}@example.com",
        username="host",
        password=hash_password("ExistingP@ss1"),
        verified=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def make_meeting(
    session: AsyncSession, host_user: User
) -> Callable[..., "asyncio.Future[Meeting]"]:
    async def _make(
        *,
        participant_cap: int = 20,
        duration: int = 15,
        status: MeetingStatus = MeetingStatus.DRAFT,
    ) -> Meeting:
        meeting = Meeting(
            user_id=host_user.id,
            title="Live contract meeting",
            description=None,
            room_code=uuid.uuid4().hex[:8],
            duration=duration,
            participant_cap=participant_cap,
            total_questions=0,
            status=status,
        )
        session.add(meeting)
        await session.commit()
        await session.refresh(meeting)
        return meeting

    return _make


@pytest_asyncio.fixture
async def meeting(make_meeting) -> Meeting:
    return await make_meeting()


# app
def build_app(*, fake_auth: bool) -> FastAPI:
    app = FastAPI()
    app.include_router(live_router.websocket_router)
    if fake_auth:

        async def host_auth(websocket: WebSocket) -> None:
            websocket.state.user = fake_user(uuid.UUID(websocket.query_params["uid"]))

        async def participant_auth(
            websocket: WebSocket, meeting_id: uuid.UUID = Path()
        ) -> None:
            websocket.state.participant_id = uuid.UUID(websocket.query_params["pid"])
            websocket.state.meeting_id = meeting_id

        app.dependency_overrides[get_current_user_websocket] = host_auth
        app.dependency_overrides[get_current_participant_websocket] = participant_auth
    return app


async def _run_harness(
    app: FastAPI,
    meeting: Meeting,
    host_user: User,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[LiveHarness, None]:
    harness = LiveHarness(app, meeting.id, host_user.id)

    original_send = StarletteWebSocket.send

    async def send(self: StarletteWebSocket, message) -> None:
        conn = self.query_params.get("conn")
        if conn in harness.broken_connections:
            raise RuntimeError("simulated dead socket")
        if conn in harness.hung_connections:
            harness.hung_sends += 1
            # a future nothing else references: only the awaiting task holds it
            await asyncio.get_running_loop().create_future()
        await original_send(self, message)

    monkeypatch.setattr(StarletteWebSocket, "send", send)

    await harness.start()
    try:
        yield harness
    finally:
        await harness.stop()
    if request.node.get_closest_marker("expects_server_error") is None:
        assert harness.server_errors == [], (
            f"unhandled exception(s) escaped the ASGI app: {harness.server_errors!r}"
        )


@pytest_asyncio.fixture
async def live(
    meeting: Meeting,
    host_user: User,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[LiveHarness, None]:
    """Harness with fake authentication dependencies."""
    async for harness in _run_harness(
        build_app(fake_auth=True), meeting, host_user, request, monkeypatch
    ):
        yield harness


@pytest_asyncio.fixture
async def live_real_auth(
    meeting: Meeting,
    host_user: User,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[LiveHarness, None]:
    """Harness with the real JWT dependencies (no overrides)."""
    async for harness in _run_harness(
        build_app(fake_auth=False), meeting, host_user, request, monkeypatch
    ):
        yield harness


# service stubs
@pytest.fixture
def ai_summary(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Stub the OpenAI call behind ``get_snapshot``; returns a valid snapshot."""
    stub = AsyncMock(
        return_value=json.dumps(
            {
                "mood": "positive",
                "attention_flag": "none",
                "suggested_question_prompt": "What next?",
            }
        )
    )
    monkeypatch.setattr("src.live.service._get_ai_summary", stub)
    return stub


@pytest.fixture
def failing_question_insert(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make persisting an ``add_question`` fail."""

    async def boom(*args, **kwargs):
        raise RuntimeError("insert failed")

    monkeypatch.setattr("src.live.service.insert_question", boom)
