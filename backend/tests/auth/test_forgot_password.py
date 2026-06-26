from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import service as auth_service
from src.auth.repository import get_reset_password_token, get_user
from src.auth.token import check_reset_password_cooldown
from src.models import User

FORGOT_URL = "/auth/forgot-password"


async def test_forgot_password_user_not_in_db(
    client: AsyncClient,
    session: AsyncSession,
    nonexistent_forgot_password_payload: dict[str, str],
) -> None:
    """Email not in DB -> 200 (don't reveal user existence)."""
    user = await get_user(
        db=session, email=nonexistent_forgot_password_payload["email"]
    )
    assert user is None

    response = await client.post(FORGOT_URL, json=nonexistent_forgot_password_payload)
    assert response.status_code == 200  # follows best practices


async def test_forgot_password_token_not_in_db(
    client: AsyncClient, session: AsyncSession, forgot_password_user: User
) -> None:
    """Valid user, no existing token -> token created, email sent, 200."""
    token = await get_reset_password_token(db=session, u_id=forgot_password_user.id)
    assert token is None

    response = await client.post(FORGOT_URL, json={"email": forgot_password_user.email})
    assert response.status_code == 200

    token = await get_reset_password_token(db=session, u_id=forgot_password_user.id)
    assert token is not None

    auth_service.send_reset_password_email.assert_awaited_once()  # ty:ignore[unresolved-attribute]


async def test_forgot_password_token_cooldown_not_elapsed(
    client: AsyncClient, session: AsyncSession, forgot_password_user_with_token: User
) -> None:
    """Valid user, token cooldown not elapsed -> no new token, no email sent, 200."""
    token = await get_reset_password_token(
        db=session, u_id=forgot_password_user_with_token.id
    )
    assert token is not None
    assert check_reset_password_cooldown(token.created_at) is False
    prev_token_id = token.id

    response = await client.post(
        FORGOT_URL, json={"email": forgot_password_user_with_token.email}
    )
    assert response.status_code == 200  # user must still think the token was sent
    curr_token = await get_reset_password_token(
        db=session, u_id=forgot_password_user_with_token.id
    )
    assert curr_token is not None
    assert curr_token.id == prev_token_id


async def test_forgot_password_token_cooldown_elapsed(
    client: AsyncClient,
    session: AsyncSession,
    forgot_password_user_expired_cooldown: User,
) -> None:
    """Valid user, token cooldown elapsed -> new token created, email sent, 200."""
    token = await get_reset_password_token(
        db=session, u_id=forgot_password_user_expired_cooldown.id
    )
    assert token is not None
    assert check_reset_password_cooldown(token.created_at) is True
    prev_token_id = token.id

    response = await client.post(
        FORGOT_URL, json={"email": forgot_password_user_expired_cooldown.email}
    )
    assert response.status_code == 200

    curr_token = await get_reset_password_token(
        db=session, u_id=forgot_password_user_expired_cooldown.id
    )
    assert curr_token is not None
    assert (
        check_reset_password_cooldown(curr_token.created_at) is False
    )  # cooldown has not elapsed
    assert curr_token.id != prev_token_id  # a new reset password token has been made
    auth_service.send_reset_password_email.assert_awaited_once()  # ty:ignore[unresolved-attribute]


async def test_forgot_password_unverified_user(
    client: AsyncClient, session: AsyncSession, unverified_user: User
) -> None:
    response = await client.post(FORGOT_URL, json={"email": unverified_user.email})
    assert response.status_code == 200

    token = await get_reset_password_token(db=session, u_id=unverified_user.id)
    assert token is None
