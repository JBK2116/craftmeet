import datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import service as auth_service
from src.auth.crypto import check_password
from src.auth.repository import get_user, get_verify_email_token
from src.models import User

SIGNUP_URL = "/auth/signup"


async def test_signup_new_user(
    client: AsyncClient, session: AsyncSession, signup_payload: dict[str, str]
) -> None:
    """Fresh user signs up — user, verify-email token created, verification email sent, 201."""
    response = await client.post(url=SIGNUP_URL, json=signup_payload)
    assert response.status_code == 201

    updated_user = await get_user(db=session, email=signup_payload["email"])
    assert updated_user is not None
    assert updated_user.password is not None
    assert updated_user.username == signup_payload["username"]
    assert (
        check_password(raw=signup_payload["password"], hashed=updated_user.password)
        is True
    )

    created_token = await get_verify_email_token(db=session, u_id=updated_user.id)
    assert created_token is not None
    assert created_token.expires_at > datetime.datetime.now(datetime.UTC).replace(
        tzinfo=None
    )
    auth_service.send_verification_email.assert_awaited_once()  # ty:ignore[unresolved-attribute]
    return


async def test_signup_unverified_user(
    client: AsyncClient,
    session: AsyncSession,
    unverified_user: User,
    alternate_signup_payload: dict[str, str],
) -> None:
    """Unverified user without an existing token re-signs up — token created, password/username updated, email sent, 201."""
    old_username = unverified_user.username
    old_password_hash = unverified_user.password

    response = await client.post(
        url=SIGNUP_URL,
        json={
            "username": alternate_signup_payload["username"],
            "email": unverified_user.email,
            "password": alternate_signup_payload["password"],
        },
    )
    assert response.status_code == 201
    # In this case, the user's details should just be updated

    updated_user = await get_user(db=session, email=unverified_user.email)
    assert updated_user is not None
    assert updated_user.password is not None
    assert updated_user.username != old_username  # username was updated
    assert updated_user.password != old_password_hash  # password hash was updated

    created_token = await get_verify_email_token(db=session, u_id=updated_user.id)
    assert created_token is not None
    assert created_token.expires_at > datetime.datetime.now(datetime.UTC).replace(
        tzinfo=None
    )

    auth_service.send_verification_email.assert_awaited_once()  # ty:ignore[unresolved-attribute]
    return


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
    assert "exists" in response.json()["message"]


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
    assert "wait" in response.json()["message"]
    return


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
    auth_service.send_verification_email.assert_awaited_once()  # ty:ignore[unresolved-attribute]
    return
