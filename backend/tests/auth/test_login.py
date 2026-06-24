import datetime

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import service as auth_service
from src.auth.crypto import hash_password
from src.auth.repository import get_refresh_token, get_user, get_verify_email_token
from src.models import User

LOGIN_URL = "/auth/login"


@pytest_asyncio.fixture
async def verified_login_user(session: AsyncSession) -> User:
    """A verified user for the successful login test.

    Uses a distinct email so it doesn't collide with ``verified_user``
    from ``conftest.py`` when both are used in the same module.
    """
    user = User(
        email="verified-login@example.com",
        username="verifiedlogin",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def test_login_missing_user(
    client: AsyncClient,
    session: AsyncSession,
    nonexistent_login_payload: dict[str, str],
) -> None:
    """Email not in DB -> 401 INVALID_CREDENTIALS."""
    user = await get_user(db=session, email=nonexistent_login_payload["email"])
    assert user is None

    response = await client.post(url=LOGIN_URL, json=nonexistent_login_payload)
    assert response.status_code == 401
    assert response.json()["type"] == "invalid_credentials"


async def test_login_oauth_user(
    client: AsyncClient,
    session: AsyncSession,
    oauth_user: User,
    oauth_login_payload: dict[str, str],
) -> None:
    """OAuth user (password=None) tries password login -> 401 INVALID_CREDENTIALS."""
    user = await get_user(db=session, email=oauth_user.email)
    assert user is not None
    assert user.password is None
    assert user.google_id is not None

    response = await client.post(LOGIN_URL, json=oauth_login_payload)
    assert response.status_code == 401
    assert response.json()["type"] == "invalid_credentials"


async def test_login_invalid_password(
    client: AsyncClient,
    session: AsyncSession,
    verified_user: User,
    invalid_login_payload: dict[str, str],
) -> None:
    """Correct email, wrong password -> 401 INVALID_CREDENTIALS."""
    user = await get_user(db=session, email=verified_user.email)
    assert user is not None
    assert user.password is not None

    response = await client.post(LOGIN_URL, json=invalid_login_payload)
    assert response.status_code == 401
    assert response.json()["type"] == "invalid_credentials"


async def test_login_unverified_user_no_token(
    client: AsyncClient,
    session: AsyncSession,
    unverified_user: User,
) -> None:
    """Unverified user without a verify-email token -> token created, email sent, 401."""
    token_before = await get_verify_email_token(db=session, u_id=unverified_user.id)
    assert token_before is None

    response = await client.post(
        LOGIN_URL,
        json={
            "email": unverified_user.email,
            "password": "ValidP@ss1234",
        },
    )
    assert response.status_code == 401
    assert response.json()["type"] == "email_not_verified"

    token_after = await get_verify_email_token(db=session, u_id=unverified_user.id)
    assert token_after is not None
    assert token_after.expires_at > datetime.datetime.now(datetime.UTC).replace(
        tzinfo=None
    )

    auth_service.send_verification_email.assert_awaited_once()  # ty:ignore[unresolved-attribute]


async def test_login_unverified_user_active_cooldown(
    client: AsyncClient,
    session: AsyncSession,
    unverified_user_with_token: User,
) -> None:
    """Unverified user whose token cooldown has not elapsed -> 401, no email sent."""
    token = await get_verify_email_token(db=session, u_id=unverified_user_with_token.id)
    assert token is not None

    response = await client.post(
        LOGIN_URL,
        json={
            "email": unverified_user_with_token.email,
            "password": "ExistingP@ss1",
        },
    )
    assert response.status_code == 401
    assert response.json()["type"] == "email_not_verified"

    # Cooldown not elapsed -> service must NOT call send_verification_email
    auth_service.send_verification_email.assert_not_awaited()  # ty:ignore[unresolved-attribute]


async def test_login_unverified_user_expired_cooldown(
    client: AsyncClient,
    session: AsyncSession,
    unverified_user_expired_cooldown: User,
) -> None:
    """Unverified user whose token cooldown has elapsed -> token rotated, email re-sent, 401."""
    old_token = await get_verify_email_token(
        db=session, u_id=unverified_user_expired_cooldown.id
    )
    assert old_token is not None

    response = await client.post(
        LOGIN_URL,
        json={
            "email": unverified_user_expired_cooldown.email,
            "password": "ExistingP@ss1",
        },
    )
    assert response.status_code == 401
    assert response.json()["type"] == "email_not_verified"

    # Old token should be deleted and a fresh one inserted
    new_token = await get_verify_email_token(
        db=session, u_id=unverified_user_expired_cooldown.id
    )
    assert new_token is not None
    assert new_token.id != old_token.id

    auth_service.send_verification_email.assert_awaited_once()  # ty:ignore[unresolved-attribute]


async def test_login_verified_user(
    client: AsyncClient,
    session: AsyncSession,
    verified_login_user: User,
) -> None:
    """Verified user with valid credentials -> 200, cookies set, user returned."""
    response = await client.post(
        LOGIN_URL,
        json={
            "email": verified_login_user.email,
            "password": "ExistingP@ss1",
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert body["email"] == verified_login_user.email
    assert body["username"] == verified_login_user.username
    assert body["id"] == str(verified_login_user.id)
    assert body["verified"] is True

    # JWT cookies set in the response
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    # Refresh token persisted in the database
    refresh = await get_refresh_token(db=session, u_id=verified_login_user.id)
    assert refresh is not None


@pytest_asyncio.fixture
async def multiple_login_user(session: AsyncSession) -> User:
    """A verified user for the multiple-login test.

    Uses a distinct email so it doesn't collide with
    ``verified_login_user`` when both are used in the same module.
    """
    user = User(
        email="multiple-login@example.com",
        username="multiplelogin",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def test_login_multiple_users(
    client: AsyncClient, session: AsyncSession, multiple_login_user: User
) -> None:
    response = await client.post(
        LOGIN_URL,
        json={
            "email": multiple_login_user.email,
            "password": "ExistingP@ss1",
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert body["email"] == multiple_login_user.email
    assert body["username"] == multiple_login_user.username
    assert body["id"] == str(multiple_login_user.id)
    assert body["verified"] is True

    # JWT cookies set in the response
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    # Refresh token persisted in the database
    refresh = await get_refresh_token(db=session, u_id=multiple_login_user.id)
    assert refresh is not None
    old_refresh_id = refresh.id
    old_refresh_hash = refresh.token_hash

    response_second = await client.post(
        LOGIN_URL,
        json={
            "email": multiple_login_user.email,
            "password": "ExistingP@ss1",
        },
    )
    assert response_second.status_code == 200

    body = response_second.json()
    assert body["email"] == multiple_login_user.email
    assert body["username"] == multiple_login_user.username
    assert body["id"] == str(multiple_login_user.id)
    assert body["verified"] is True

    # JWT cookies set in the response
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    new_refresh = await get_refresh_token(db=session, u_id=multiple_login_user.id)
    assert new_refresh is not None
    assert new_refresh.id != old_refresh_id

    old_refresh_token = await get_refresh_token(db=session, token_hash=old_refresh_hash)
    assert old_refresh_token is None
