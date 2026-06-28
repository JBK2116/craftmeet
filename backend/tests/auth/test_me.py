from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import get_user
from src.auth.schemas import UserOut

ME_URL = "/auth/me"


async def test_me_invalid_access_token(client: AsyncClient) -> None:
    """Malformed access token -> 401."""
    client.cookies.set(
        "access_token",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.KMUFsIDTnFmyG3nMiGM6H9FNFUROf3wh7SmqJp-QV30",
    )
    response = await client.get(
        ME_URL,
    )
    assert response.status_code == 401


async def test_me_missing_access_token(client: AsyncClient) -> None:
    """No access token cookie -> 401."""
    response = await client.get(ME_URL)
    assert response.status_code == 401


async def test_me_invalid_access_token_type(
    client: AsyncClient, refresh_token_jwt: str
) -> None:
    """Refresh token sent as access token -> 401."""
    client.cookies.set("access_token", refresh_token_jwt)
    response = await client.get(ME_URL)
    assert response.status_code == 401


async def test_me_orphan_access_token(
    client: AsyncClient, orphan_access_token_jwt: str
) -> None:
    """Valid JWT for a non-existent user -> 401."""
    client.cookies.set("access_token", orphan_access_token_jwt)
    response = await client.get(ME_URL)
    assert response.status_code == 401


async def test_me_valid_access_token(
    client: AsyncClient, session: AsyncSession, access_token_jwt: str
) -> None:
    """Valid access token -> 200, user returned."""
    client.cookies.set("access_token", access_token_jwt)
    response = await client.get(ME_URL)
    assert response.status_code == 200

    body = response.json()
    response_body = UserOut.model_validate(body)

    user = await get_user(db=session, u_id=response_body.id)
    assert user is not None
    assert user.id == response_body.id
