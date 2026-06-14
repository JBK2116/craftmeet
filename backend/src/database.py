"""Global Database configuration and session management

This module sets up the async SQLAlchemy engine and session factory using
``asyncpg`` as the underlying PostgreSQL driver.

Exmaple Usage

    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.database import get_db

    @router.get("/items")
    async def get_items(db: AsyncSession = Depends(get_db)):
        ...
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from src.config import get_settings

_settings = get_settings()

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{_settings.DB_USER}:{_settings.DB_PASSWORD}"
    f"@{_settings.DB_HOST}:{_settings.DB_PORT}"
    f"/{_settings.DB_NAME}"
)

engine = create_async_engine(DATABASE_URL, echo=False)

Base = declarative_base()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
"""Session factory for creating ``AsyncSession`` instances.

``expire_on_commit=False`` prevents SQLAlchemy from expiring ORM attributes
after a commit, which avoids implicit lazy-load errors in async contexts.
"""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for use as a FastAPI dependency.

    Opens an ``AsyncSession`` and begins an explicit transaction for the
    duration of a request. The caller is responsible for committing via
    ``await db.commit()``. On any unhandled exception the transaction is
    rolled back automatically, ensuring partial writes never persist.

    Yields:
        AsyncSession: An active SQLAlchemy async session bound to the
        configured PostgreSQL database.

    Example::

        @router.post("/items")
        async def create_item(
            payload: ItemCreate,
            db: AsyncSession = Depends(get_db),
        ):
            db.add(Item(**payload.model_dump()))
            await db.flush()   # stage within the open transaction
            await db.commit()  # caller decides when to commit
    """
    async with AsyncSessionLocal() as session:
        await session.begin()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
