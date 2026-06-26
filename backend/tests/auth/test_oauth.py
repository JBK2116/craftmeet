from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import get_refresh_token, get_user
from src.models import User

CALLBACK_URL = "/auth/google/callback"


async def test_google_callback_oauth_exchange_fails(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OAuth token exchange raises -> 302 redirect to login?error=oauth_failed."""
    monkeypatch.setattr(
        "src.auth.router.oauth.google.authorize_access_token",
        AsyncMock(side_effect=Exception("OAuth provider error")),
    )

    response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert (
        response.headers["location"] == "http://localhost:5173/login?error=oauth_failed"
    )


async def test_google_callback_missing_userinfo(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token without userinfo -> 302 redirect to login?error=oauth_failed."""
    monkeypatch.setattr(
        "src.auth.router.oauth.google.authorize_access_token",
        AsyncMock(return_value={}),
    )

    response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert (
        response.headers["location"] == "http://localhost:5173/login?error=oauth_failed"
    )


async def test_google_callback_new_user(
    client: AsyncClient, session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Email not in DB -> user created, verified, redirected to dashboard with cookies."""
    email = "google-fresh-user@example.com"
    google_sub = "google-sub-fresh-12345"
    monkeypatch.setattr(
        "src.auth.router.oauth.google.authorize_access_token",
        AsyncMock(return_value={"userinfo": {"email": email, "sub": google_sub}}),
    )

    response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:5173/dashboard"
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    user = await get_user(db=session, email=email)
    assert user is not None
    assert user.google_id == google_sub
    assert user.verified is True
    assert user.verified_at is not None
    assert user.password is None  # OAuth user has no password

    token = await get_refresh_token(db=session, u_id=user.id)
    assert token is not None
    assert token.token_hash == response.cookies["refresh_token"]


async def test_google_callback_existing_unverified_link(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    google_unverified_unlinked_user: User,
) -> None:
    """Unverified user without google_id -> linked, verified, redirected to dashboard."""
    user_info = {
        "email": google_unverified_unlinked_user.email,
        "sub": "google-sub-unver-link-11111",
    }
    monkeypatch.setattr(
        "src.auth.router.oauth.google.authorize_access_token",
        AsyncMock(return_value={"userinfo": user_info}),
    )

    response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:5173/dashboard"
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    await session.refresh(google_unverified_unlinked_user)
    assert google_unverified_unlinked_user.google_id == "google-sub-unver-link-11111"
    assert google_unverified_unlinked_user.verified is True
    assert google_unverified_unlinked_user.verified_at is not None

    token = await get_refresh_token(db=session, u_id=google_unverified_unlinked_user.id)
    assert token is not None


async def test_google_callback_existing_verified_link(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    google_unlinked_user: User,
) -> None:
    """Verified user without google_id -> linked, redirected to dashboard."""
    user_info = {
        "email": google_unlinked_user.email,
        "sub": "google-sub-unlinked-67890",
    }
    monkeypatch.setattr(
        "src.auth.router.oauth.google.authorize_access_token",
        AsyncMock(return_value={"userinfo": user_info}),
    )

    response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:5173/dashboard"
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    await session.refresh(google_unlinked_user)
    assert google_unlinked_user.google_id == "google-sub-unlinked-67890"
    assert google_unlinked_user.verified is True  # unchanged
    assert google_unlinked_user.password is not None  # unchanged

    token = await get_refresh_token(db=session, u_id=google_unlinked_user.id)
    assert token is not None


async def test_google_callback_already_linked(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    google_linked_user: User,
) -> None:
    """User already has google_id -> user record unchanged, tokens rotated, redirected to dashboard."""
    user_info = {
        "email": google_linked_user.email,
        "sub": google_linked_user.google_id,
    }
    monkeypatch.setattr(
        "src.auth.router.oauth.google.authorize_access_token",
        AsyncMock(return_value={"userinfo": user_info}),
    )

    response = await client.get(CALLBACK_URL)

    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:5173/dashboard"
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    await session.refresh(google_linked_user)
    assert google_linked_user.google_id == "google-sub-linked-22222"  # unchanged
    assert google_linked_user.verified is True  # unchanged

    token = await get_refresh_token(db=session, u_id=google_linked_user.id)
    assert token is not None
