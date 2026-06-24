"""Auth-specific fixtures for signup and related tests.

Provides pre-created user records and signup payloads covering the three
signup scenarios:
- Fresh user (not in DB)
- Unverified existing user (with and without an existing verify token)
- Verified existing user
"""

import datetime
import secrets

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.constants import (
    VERIFY_EMAIL_TOKEN_BYTES,
    VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES,
)
from src.auth.crypto import hash_password
from src.auth.models import VerifyEmailToken
from src.models import User


@pytest_asyncio.fixture
async def signup_payload() -> dict[str, str]:
    """A valid signup request payload for a fresh user."""
    return {
        "username": "newuser",
        "email": "fresh@example.com",
        "password": "ValidP@ss1234",
    }


@pytest_asyncio.fixture
async def alternate_signup_payload() -> dict[str, str]:
    """A signup payload with different credentials than the default fixtures.

    Use when testing the paths that update an existing unverified user's
    username and password (i.e. they differ from what was set during
    fixture creation).
    """
    return {
        "username": "updateduser",
        "email": "unverified@example.com",
        "password": "NewValidP@ss1",
    }


@pytest_asyncio.fixture
async def unverified_user(session: AsyncSession) -> User:
    """A user inserted into the db with ``verified=False`` and no verify-email token row."""
    user = User(
        email="unverified@example.com",
        username="unverifieduser",
        password=hash_password("ValidP@ss1234"),
        verified=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def verified_user(session: AsyncSession) -> User:
    """A user inserted in the db with ``verified=True`` (signup should return 409)."""
    user = User(
        email="verified@example.com",
        username="verifieduser",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unverified_user_with_token(session: AsyncSession) -> User:
    """An unverified user that already has a ``VerifyEmailToken`` (cooldown not elapsed).

    The token was created moments ago, so the 1-minute cooldown has *not*
    passed — signup should raise ``VerifyEmailTokenCooldownError`` (400).
    """
    user = User(
        email="tokenuser@example.com",
        username="tokenuser",
        password=hash_password("ExistingP@ss1"),
        verified=False,
    )
    session.add(user)
    await session.flush()

    token = VerifyEmailToken(
        user_id=user.id,
        token_hash=secrets.token_urlsafe(VERIFY_EMAIL_TOKEN_BYTES),
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(minutes=VERIFY_EMAIL_TOKEN_MAX_DURATION_MINUTES),
    )
    session.add(token)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def unverified_user_expired_cooldown(session: AsyncSession) -> User:
    """An unverified user whose existing token's cooldown *has* elapsed.

    The token was created 2 minutes ago (cooldown is 1 minute), so signup
    should delete it, create a fresh one, and send the email.
    """
    user = User(
        email="cooldownuser@example.com",
        username="cooldownuser",
        password=hash_password("ExistingP@ss1"),
        verified=False,
    )
    session.add(user)
    await session.flush()

    token = VerifyEmailToken(
        user_id=user.id,
        token_hash=secrets.token_urlsafe(VERIFY_EMAIL_TOKEN_BYTES),
        expires_at=datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(hours=24),
        created_at=datetime.datetime.now(tz=datetime.UTC)
        - datetime.timedelta(minutes=2),
    )
    session.add(token)
    await session.commit()
    await session.refresh(user)
    return user
