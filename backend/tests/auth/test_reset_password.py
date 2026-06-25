import datetime
import secrets

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.constants import RESET_PASSWORD_TOKEN_BYTES
from src.auth.crypto import check_password
from src.auth.models import RefreshToken
from src.auth.repository import get_refresh_token, get_reset_password_token, get_user
from src.models import User

RESET_URL = "/auth/reset-password"
NEW_VALID_PASSWORD = "ExistingP@ss12345"  # noqa: S105

update_payload = {
    "password": NEW_VALID_PASSWORD,
    "confirm_password": NEW_VALID_PASSWORD,
}


async def test_reset_password_nonexistent_token(client: AsyncClient) -> None:
    """Random token not in DB -> 400."""
    fake_token = secrets.token_urlsafe(RESET_PASSWORD_TOKEN_BYTES)
    update_payload["token"] = fake_token

    response = await client.post(url=RESET_URL, json=update_payload)
    assert response.status_code == 400


async def test_reset_password_expired_token(
    client: AsyncClient,
    session: AsyncSession,
    reset_password_user_expired_token: tuple[User, str],
) -> None:
    """Expired reset token -> 400, password not changed."""
    user = reset_password_user_expired_token[0]
    raw_token = reset_password_user_expired_token[1]
    update_payload["token"] = raw_token

    assert user.password is not None
    current_id = user.id

    response = await client.post(url=RESET_URL, json=update_payload)
    assert response.status_code == 400

    user = await get_user(db=session, u_id=current_id)
    assert user is not None
    assert user.password is not None
    assert check_password(raw=NEW_VALID_PASSWORD, hashed=user.password) is False


async def test_reset_password_used_token(
    client: AsyncClient,
    session: AsyncSession,
    reset_password_user_used_token: tuple[User, str],
) -> None:
    """Already-used reset token -> 400, password not changed."""
    user = reset_password_user_used_token[0]
    raw_token = reset_password_user_used_token[1]
    update_payload["token"] = raw_token

    assert user.password is not None
    current_id = user.id

    response = await client.post(url=RESET_URL, json=update_payload)
    assert response.status_code == 400

    user = await get_user(db=session, u_id=current_id)
    assert user is not None
    assert user.password is not None
    assert check_password(raw=NEW_VALID_PASSWORD, hashed=user.password) is False


async def test_reset_password_orphan_token(
    client: AsyncClient, session: AsyncSession, reset_password_orphan_token: str
) -> None:
    """Token whose user_id doesn't match any user -> 400."""
    token = await get_reset_password_token(
        db=session, token_val=reset_password_orphan_token
    )
    assert token is not None
    user = await get_user(db=session, u_id=token.user_id)
    assert user is None

    update_payload["token"] = reset_password_orphan_token

    response = await client.post(url=RESET_URL, json=update_payload)
    assert response.status_code == 400


async def test_reset_password_valid_tokne(
    client: AsyncClient,
    session: AsyncSession,
    reset_password_user_with_token: tuple[User, str],
) -> None:
    """Valid (unexpired, unused) reset token -> 200, password updated."""
    user = reset_password_user_with_token[0]
    raw_token = reset_password_user_with_token[1]
    update_payload["token"] = raw_token

    curr_id = user.id

    response = await client.post(RESET_URL, json=update_payload)
    assert response.status_code == 200

    updated_user = await get_user(db=session, u_id=curr_id)
    assert updated_user is not None
    assert updated_user.password is not None
    assert (
        check_password(raw=update_payload["password"], hashed=updated_user.password)
        is True
    )


async def test_reset_password_success_side_effects(
    client: AsyncClient,
    session: AsyncSession,
    reset_password_user_with_token: tuple[User, str],
) -> None:
    """Valid reset -> 200, token marked used, refresh tokens revoked."""
    user = reset_password_user_with_token[0]
    raw_token = reset_password_user_with_token[1]
    update_payload["token"] = raw_token

    # Insert a refresh token to verify it gets deleted on reset
    refresh = RefreshToken(
        user_id=user.id,
        token_hash=secrets.token_urlsafe(32),
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=24),
    )
    session.add(refresh)
    await session.commit()

    curr_id = user.id

    response = await client.post(RESET_URL, json=update_payload)
    assert response.status_code == 200

    # Password was updated
    updated_user = await get_user(db=session, u_id=curr_id)
    assert updated_user is not None
    assert updated_user.password is not None
    assert (
        check_password(raw=update_payload["password"], hashed=updated_user.password)
        is True
    )

    # Token was marked as used (prevents replay)
    used_token = await get_reset_password_token(db=session, token_val=raw_token)
    assert used_token is not None
    assert used_token.used_at is not None

    # All refresh tokens were deleted (invalidates existing sessions)
    deleted_refresh = await get_refresh_token(db=session, u_id=curr_id)
    assert deleted_refresh is None
