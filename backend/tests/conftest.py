"""Test configuration, fixtures, and database setup.

Provides the async SQLAlchemy engine, isolated per-test sessions with
savepoint rollback, and an HTTP client wired to the FastAPI app with
the test database injected.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import ARRAY, event
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, SessionTransaction
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.compiler import SQLCompiler

from src.database import Base, get_db


# SQLite compatibility
# The MultipleChoiceResponse model uses PostgreSQL's ARRAY(Integer),
# which SQLite cannot render natively.  This compilation hook tells
# SQLAlchemy to store ARRAY columns as JSON text when running against
# the SQLite dialect.
@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_element: ARRAY, compiler: SQLCompiler, **kw: Any) -> str:  # noqa: ARG001
    return compiler.process(SQLITE_JSON(), **kw)


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Provide a session-scoped event loop for async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create the test database engine once per session.

    All tables are created at session scope so that individual test
    functions do not pay the DDL cost. ``StaticPool`` is required —
    without it, every checkout from the pool gets its own brand-new
    in-memory SQLite database, so the tables created here would be
    invisible to the connections used by the ``session`` fixture.
    """
    async_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(async_engine.sync_engine, "connect")
    def do_connect(dbapi_connection, connection_record):
        """Disable aiosqlite's emitting of the BEGIN statement entirely."""
        dbapi_connection.isolation_level = None

    @event.listens_for(async_engine.sync_engine, "begin")
    def do_begin(conn):
        """Emit our own BEGIN."""
        conn.exec_driver_sql("BEGIN")

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_engine
    await async_engine.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session per test.

    The fixture opens a connection-level transaction (outer) and a
    savepoint (nested). Service code that calls ``await db.commit()``
    commits the savepoint, not the outer transaction. The
    ``after_transaction_end`` listener below restarts a fresh savepoint
    every time one ends, so a *second* (or third...) commit within the
    same test still nests inside the outer transaction instead of
    committing it directly — which would make it unrollback-able at
    teardown and leak data into the next test.

    After the test, the outer transaction is rolled back, undoing
    **all** changes — guaranteeing test isolation without manual
    cleanup.
    """
    connection = await engine.connect()
    transaction = await connection.begin()
    test_session = AsyncSession(bind=connection, expire_on_commit=False)

    await test_session.begin_nested()

    @event.listens_for(test_session.sync_session, "after_transaction_end")
    def _restart_savepoint(
        sync_session: Session, transaction: SessionTransaction
    ) -> None:
        parent = transaction._parent
        if transaction.nested and parent is not None and not parent.nested:
            sync_session.begin_nested()

    try:
        yield test_session
    finally:
        await test_session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP client with the test database injected.

    Overrides the ``get_db`` dependency so that all requests made
    through this client operate on the isolated test session.
    """
    # Import here to avoid triggering side effects at module load
    # (e.g. OAuth registration via the auth router import).
    from main import app

    app.dependency_overrides[get_db] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        yield ac
    # Only remove our own override — clear() would also wipe overrides
    # set by other fixtures/tests.
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture(autouse=True)
async def _mock_email_sending(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent real email sending with sendgrid during tests."""
    monkeypatch.setattr("src.auth.service.send_verification_email", AsyncMock())
    monkeypatch.setattr("src.auth.service.send_reset_password_email", AsyncMock())
