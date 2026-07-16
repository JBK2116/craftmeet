"""
This module stores global utility functions used throughout the codebase
"""

import asyncio
import logging

from fastapi import Request

from src.models import User

logger = logging.getLogger(__name__)


def set_timeout(callback, delay_seconds: float, *args, **kwargs) -> asyncio.Task:
    """
    Schedule a callback to be called after a delay.

    Args:
        callback: The async callable to invoke after the delay.
        delay_seconds: Time in seconds to wait before calling callback.
        *args: Additional positional arguments to pass to callback.
        **kwargs: Additional keyword arguments to pass to callback.

    Returns:
        asyncio.Task representing the scheduled timeout.
    """

    async def _waiter():
        await asyncio.sleep(delay_seconds)
        await callback(*args, **kwargs)

    return asyncio.create_task(_waiter())


def generate_participants_meeting_access_token_key(m_id: str) -> str:
    """
    Generate a key string to identify a participant's access token for a specific meeting.

    Args:
        m_id (str): The meeting's unique identifier.

    Returns:
        str: A formatted key string prefixed with "participants_meeting_access_token_".
    """
    return f"participants_meeting_access_token_{m_id}"


def ip_or_user_key_func(request: Request) -> str:
    """Generate a unique key for rate limiting based on IP or user ID.

    If a user is authenticated, return the user's ID as the key.
    Otherwise, return the client's IP address as the key.
    """
    user: User | None = getattr(request.state, "user", None)
    if user is None:
        logger.debug("user not found in request. limiting with client ip.")
        client = request.client
        if client is not None:
            logger.debug("rate limiting with client ip", extra={"ip": client.host})
            return f"ip:{client.host}"
        else:
            logger.debug(
                "client ip not found in request. limiting with unknown variable."
            )
            return "ip:unknown"
    else:
        logger.debug(
            "user found in request. limiting with user_id",
            extra={"user_id": str(user.id)},
        )
        return f"uid:{str(user.id)}"
