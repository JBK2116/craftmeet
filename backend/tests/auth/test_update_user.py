from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import get_user
from src.models import User

UPDATE_URL = "/auth/me"
UPDATE_PAYLOAD = {"username": "johndoe"}


async def test_update_user_missing_access_token(client: AsyncClient) -> None:
    """No access token cookie present — should return 401."""
    response = await client.patch(UPDATE_URL, json=UPDATE_PAYLOAD)
    assert response.status_code == 401


async def test_update_user_invalid_access_token(client: AsyncClient) -> None:
    """Access token cookie is present but malformed/invalid — should return 401."""
    response = await client.patch(UPDATE_URL, json=UPDATE_PAYLOAD)
    assert response.status_code == 401


async def test_update_user_expired_access_token(
    client: AsyncClient, expired_access_token_jwt: str
) -> None:
    """Access token has expired — decode should fail, returns 401."""
    client.cookies.set("access_token", expired_access_token_jwt)

    response = await client.patch(UPDATE_URL, json=UPDATE_PAYLOAD)
    assert response.status_code == 401


async def test_update_user_orphan_access_token(
    client: AsyncClient, orphan_access_token_jwt: str
) -> None:
    """Token is structurally valid but user does not exist — should return 401."""
    client.cookies.set("access_token", orphan_access_token_jwt)

    response = await client.patch(UPDATE_URL, json=UPDATE_PAYLOAD)
    assert response.status_code == 401


async def test_update_user_valid_access_token(
    authenticated_client: AsyncClient, session: AsyncSession, verified_user: User
) -> None:
    """Valid access token — username updated in DB, returns 200."""
    u_id = verified_user.id
    prev_username = verified_user.username

    response = await authenticated_client.patch(UPDATE_URL, json=UPDATE_PAYLOAD)
    assert response.status_code == 200

    user = await get_user(db=session, u_id=u_id)
    assert user is not None
    assert prev_username != user.username
