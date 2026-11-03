from typing import Any

from cryptography.fernet import Fernet
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

from src.config import get_settings
from src.database import AsyncSessionLocal
from src.mcp.service import create_meeting_for_user, get_mcp_user
from src.meeting.schemas import MeetingIn

settings = get_settings()

auth = GoogleProvider(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    base_url=settings.MCP_BASE_URL,
    required_scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"],
    cache_ttl_seconds=60 * 5,
    jwt_signing_key=settings.JWT_SECRET_KEY,
    client_storage=FernetEncryptionWrapper(
        key_value=RedisStore(url=settings.REDIS_URL),
        fernet=Fernet(settings.MCP_STORAGE_ENCRYPTION_KEY),
    ),
)


mcp = FastMCP("Test Tool", auth=auth)

mcp_app = mcp.http_app()


@mcp.tool
async def create_meeting(meeting: MeetingIn) -> dict[str, Any]:
    """
    Create a new CraftMeet meeting with its questions from a single call.

    Use when the user wants to set up a meeting. Returns the host URL, which the user
    opens in CraftMeet to start the meeting, plus the title and question count.

    :param meeting: The contents of the meeting to create.
    :return: Metadata of the newly created meeting.
    """

    async with AsyncSessionLocal() as db:
        user = await get_mcp_user(db=db)

        out = await create_meeting_for_user(db=db, user=user, payload=meeting)
        return out
