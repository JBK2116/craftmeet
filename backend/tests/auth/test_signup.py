"""
This module handles all router level test-cases for the authentication package.
Including endpoint such as
    - Signup
    - Login
    - Forgot Password
and more
"""

from httpx import AsyncClient

from src.models import User

SIGNUP_URL = "/auth/signup"


async def test_signup_new_user(
    client: AsyncClient, signup_payload: dict[str, str]
) -> None:
    """Fresh user signs up — user, verify-email token created, verification email sent, 201."""
    response = await client.post(url=SIGNUP_URL, json=signup_payload)
    assert response.status_code == 201
    return


async def test_signup_unverified_user(
    client: AsyncClient,
    unverified_user: User,
    alternate_signup_payload: dict[str, str],
) -> None:
    """Unverified user without an existing token re-signs up — token created, password/username updated, email sent, 201."""
    response = await client.post(
        url=SIGNUP_URL,
        json={
            "username": alternate_signup_payload["username"],
            "email": unverified_user.email,
            "password": alternate_signup_payload["password"],
        },
    )
    # In this case, the user's details should just be updated
    assert response.status_code == 201


async def test_verified_user(client: AsyncClient, verified_user: User) -> None:
    """Verified user re-signs up — should get 409 (EmailExistsError)."""
    response = await client.post(
        SIGNUP_URL,
        json={
            "username": verified_user.username,
            "email": verified_user.email,
            "password": "ExistingP@ss1",
        },
    )
    assert response.status_code == 409


async def test_unverified_user_with_token(
    client: AsyncClient, unverified_user_with_token: User
) -> None:
    """Unverified user with existing token resends signup before cooldown — should get 400."""
    response = await client.post(
        url=SIGNUP_URL,
        json={
            "username": unverified_user_with_token.username,
            "email": unverified_user_with_token.email,
            "password": "ExistingP@ss1",
        },
    )
    assert response.status_code == 400


async def test_unverified_user_with_token_elapsed(
    client: AsyncClient, unverified_user_expired_cooldown: User
) -> None:
    """Unverified user with expired token cooldown re-signs up — token rotates, password/username update, email re-sent, 201."""
    response = await client.post(
        SIGNUP_URL,
        json={
            "username": unverified_user_expired_cooldown.username,
            "email": unverified_user_expired_cooldown.email,
            "password": "ExistingP@ss1",
        },
    )
    assert response.status_code == 201
