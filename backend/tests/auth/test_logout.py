import secrets
import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.constants import TOKEN_HASH_LENGTH_REFRESH_TOKEN
from src.auth.repository import get_refresh_token
from src.auth.token import generate_refresh_token
from src.models import User

LOGOUT_URL = "/auth/logout"
LOGIN_URL = "/auth/login"


async def test_logout_valid_refresh_token(
    client: AsyncClient,
    session: AsyncSession,
    verified_user: User,
    valid_login_payload: dict[str, str],
) -> None:
    """Valid refresh token in cookies -> 204, token deleted from DB."""

    login_response = await client.post(url=LOGIN_URL, json=valid_login_payload)
    assert login_response.status_code == 200
    assert "access_token" in login_response.cookies
    assert "refresh_token" in login_response.cookies

    refresh_token = await get_refresh_token(db=session, u_id=verified_user.id)
    assert refresh_token is not None
    refresh_hash = refresh_token.token_hash

    logout_response = await client.post(
        url=LOGOUT_URL, cookies={"refresh_token": refresh_token.token_hash}
    )
    # tokens are cleared
    assert "access_token" not in logout_response.cookies
    assert "refresh_token" not in logout_response.cookies
    assert logout_response.status_code == 204

    refresh_token = await get_refresh_token(db=session, token_hash=refresh_hash)
    assert refresh_token is None


async def test_logout_orphan_refresh_token(
    client: AsyncClient,
    session: AsyncSession,
    verified_user: User,
    valid_login_payload: dict[str, str],
) -> None:
    """Refresh token for a non-existent user -> 204, verified_user tokens untouched."""

    login_response = await client.post(url=LOGIN_URL, json=valid_login_payload)
    assert login_response.status_code == 200
    assert "access_token" in login_response.cookies
    assert "refresh_token" in login_response.cookies

    refresh_token = await get_refresh_token(db=session, u_id=verified_user.id)
    assert refresh_token is not None

    invalid_hash = generate_refresh_token(
        u_id=uuid.uuid4()
    ).token_hash  # token does not belong to any user

    logout_response = await client.post(
        url=LOGOUT_URL, cookies={"refresh_token": invalid_hash}
    )
    # tokens are cleared
    assert "access_token" not in logout_response.cookies
    assert "refresh_token" not in logout_response.cookies
    assert logout_response.status_code == 204

    # user's refresh tokens are not affected
    refresh_token = await get_refresh_token(db=session, u_id=verified_user.id)
    assert refresh_token is not None


async def test_logout_missing_refresh_token(
    client: AsyncClient,
    session: AsyncSession,
    verified_user: User,
    valid_login_payload: dict[str, str],
) -> None:
    """Empty string as refresh token -> 204, user tokens untouched."""

    login_response = await client.post(url=LOGIN_URL, json=valid_login_payload)
    assert login_response.status_code == 200
    assert "access_token" in login_response.cookies
    assert "refresh_token" in login_response.cookies

    refresh_token = await get_refresh_token(db=session, u_id=verified_user.id)
    assert refresh_token is not None

    logout_response = await client.post(url=LOGOUT_URL, cookies={"refresh_token": ""})
    assert logout_response.status_code == 204
    # tokens are cleared
    assert "access_token" not in logout_response.cookies
    assert "refresh_token" not in logout_response.cookies

    # user's refresh tokens are not affected
    refresh_token = await get_refresh_token(db=session, u_id=verified_user.id)
    assert refresh_token is not None


async def test_logout_invalid_refresh_token(
    client: AsyncClient,
    session: AsyncSession,
    verified_user: User,
    valid_login_payload: dict[str, str],
) -> None:
    """Malformed JWT as refresh token -> 204, user tokens untouched."""
    login_response = await client.post(url=LOGIN_URL, json=valid_login_payload)
    assert login_response.status_code == 200
    assert "access_token" in login_response.cookies
    assert "refresh_token" in login_response.cookies

    refresh_token = await get_refresh_token(db=session, u_id=verified_user.id)
    assert refresh_token is not None

    invalid_token_hash = secrets.token_urlsafe(TOKEN_HASH_LENGTH_REFRESH_TOKEN)

    logout_response = await client.post(
        url=LOGOUT_URL, cookies={"refresh_token": invalid_token_hash}
    )
    assert logout_response.status_code == 204
    # tokens are cleared
    assert "access_token" not in logout_response.cookies
    assert "refresh_token" not in logout_response.cookies

    # user's refresh tokens are not affected
    refresh_token = await get_refresh_token(db=session, u_id=verified_user.id)
    assert refresh_token is not None


async def test_logout_invalid_token_type(
    client: AsyncClient,
    session: AsyncSession,
    verified_user: User,
    valid_login_payload: dict[str, str],
    access_token_jwt: str,
) -> None:
    """Access token sent where refresh token expected -> 204, user tokens untouched."""

    login_response = await client.post(url=LOGIN_URL, json=valid_login_payload)
    assert login_response.status_code == 200
    assert "access_token" in login_response.cookies
    assert "refresh_token" in login_response.cookies

    refresh_token = await get_refresh_token(db=session, u_id=verified_user.id)
    assert refresh_token is not None

    logout_response = await client.post(
        url=LOGOUT_URL, cookies={"refresh_token": access_token_jwt}
    )
    assert logout_response.status_code == 204
    # tokens are cleared
    assert "access_token" not in logout_response.cookies
    assert "refresh_token" not in logout_response.cookies

    # user's refresh tokens are not affected
    refresh_token = await get_refresh_token(db=session, u_id=verified_user.id)
    assert refresh_token is not None
