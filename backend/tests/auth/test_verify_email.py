import secrets

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.constants import VERIFY_EMAIL_TOKEN_BYTES
from src.auth.models import VerifyEmailToken
from src.auth.repository import get_user, get_verify_email_token
from src.models import User

VERIFY_URL = "/auth/verify-email"


async def test_verify_email_orphan_token(
    client: AsyncClient,
    session: AsyncSession,
    verify_email_orphan_token: VerifyEmailToken,
) -> None:
    """Token whose user_id doesn't match any user -> 400, token deleted."""
    user_id = verify_email_orphan_token.user_id
    token_hash = verify_email_orphan_token.token_hash

    user = await get_user(db=session, u_id=user_id)
    assert user is None

    response = await client.post(
        VERIFY_URL, json={"token": verify_email_orphan_token.token_hash}
    )
    assert response.status_code == 400

    token = await get_verify_email_token(db=session, token_val=token_hash)
    assert token is None  # deleted from the database

    user = await get_user(db=session, u_id=user_id)
    assert user is None


async def test_verify_email_invalid_token(client: AsyncClient) -> None:
    """Random token not in DB -> 400."""
    invalid_token = secrets.token_urlsafe(VERIFY_EMAIL_TOKEN_BYTES)
    response = await client.post(VERIFY_URL, json={"token": invalid_token})
    assert response.status_code == 400


async def test_verify_email_expired_token(
    client: AsyncClient,
    session: AsyncSession,
    verify_email_user_expired_token: tuple[User, VerifyEmailToken],
) -> None:
    """Expired token -> 400, token kept in DB, user remains unverified."""
    user_id = verify_email_user_expired_token[0].id
    token_hash = verify_email_user_expired_token[1].token_hash

    response = await client.post(VERIFY_URL, json={"token": token_hash})
    assert response.status_code == 400

    token = await get_verify_email_token(db=session, token_val=token_hash)
    assert (
        token is not None
    )  # not deleted from the database, will be replaced when user is verified or requests another token

    user = await get_user(db=session, u_id=user_id)
    assert user is not None
    assert user.verified is False


async def test_verify_email_valid_token(
    client: AsyncClient,
    session: AsyncSession,
    verify_email_user_with_token: tuple[User, str],
) -> None:
    """Valid unexpired token for unverified user -> 200, token deleted, user verified."""
    user_id = verify_email_user_with_token[0].id
    token_hash = verify_email_user_with_token[1]

    response = await client.post(VERIFY_URL, json={"token": token_hash})
    assert response.status_code == 200

    token = await get_verify_email_token(db=session, token_val=token_hash)
    assert token is None  # deleted after use

    user = await get_user(db=session, u_id=user_id)
    assert user is not None
    assert user.verified_at is not None
    assert user.verified is True
