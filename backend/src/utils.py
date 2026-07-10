"""
This module stores global utility functions used throughout the codebase
"""
import asyncio


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
