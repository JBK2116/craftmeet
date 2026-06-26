from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import RefreshToken
from src.auth.repository import get_refresh_token

REFRESH_URL = "/auth/refresh"


async def test_refresh_missing_token(client: AsyncClient) -> None:
    """No refresh token cookie -> 401."""
    response = await client.post(REFRESH_URL)
    assert response.status_code == 401


async def test_refresh_invalid_token(client: AsyncClient) -> None:
    """Malformed/invalid JWT -> 401."""
    client.cookies.set(
        "refresh_token",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.KMUFsIDTnFmyG3nMiGM6H9FNFUROf3wh7SmqJp-QV30",
    )
    response = await client.post(REFRESH_URL)
    assert response.status_code == 401


async def test_refresh_orphan_token(
    client: AsyncClient, stored_orphan_refresh_token_jwt: str
) -> None:
    """Valid JWT for a non-existent user -> 401."""
    client.cookies.set("refresh_token", stored_orphan_refresh_token_jwt)
    response = await client.post(REFRESH_URL)
    assert response.status_code == 401


async def test_refresh_expired_token(
    client: AsyncClient, expired_refresh_token_jwt: str
) -> None:
    """Expired refresh token -> 401."""
    client.cookies.set("refresh_token", expired_refresh_token_jwt)
    response = await client.post(REFRESH_URL)
    assert response.status_code == 401


async def test_refresh_valid_token(
    client: AsyncClient, session: AsyncSession, stored_refresh_token: RefreshToken
) -> None:
    """Valid refresh token -> 200, new access and refresh tokens issued, old token replaced."""

    old = stored_refresh_token.id
    user_id = stored_refresh_token.user_id

    client.cookies.set("refresh_token", stored_refresh_token.token_hash)

    response = await client.post(REFRESH_URL)
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

    new_token = await get_refresh_token(db=session, u_id=user_id)
    assert new_token is not None
    assert new_token.id != old
