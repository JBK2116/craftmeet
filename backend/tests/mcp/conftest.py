import datetime
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
import pytest_asyncio
from fastmcp import Client
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.crypto import hash_password
from src.mcp.server import mcp
from src.models import User


class MockSessionContext:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_session_factory(session: AsyncSession) -> Callable[[], MockSessionContext]:
    """
    Returns a factory that yields the active test session
    when AsyncSessionLocal() is called in production code.
    """
    return lambda: MockSessionContext(session)


@pytest.fixture
async def mcp_client() -> AsyncIterator[Client]:
    """
    Yields the mcp application for use in tests.
    """
    async with Client(transport=mcp) as client:
        yield client


@pytest_asyncio.fixture
async def verified_user(session) -> User:
    """
    Returns a verified user already seeded into the database for use in later tests.
    :param session: AsyncSession to interact with database.
    :return: Seeded verified user object.
    """
    user = User(
        email="verified@example.com",
        username="verifieduser",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
def unverified_user() -> User:
    """
    Returns a unverified user not seeded into the database.
    """
    return User(
        email="unverified@example.com",
        username="unverifieduser",
        password=hash_password("ExistingP@ss1"),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )


@pytest.fixture
def valid_meeting() -> dict[str, Any]:
    """
    Returns a valid MeetingIn object structure matching the Pydantic sub-schemas.
    """
    return {
        "title": "Sprint Retro",
        "description": "End-of-sprint retrospective",
        "duration": 30,
        "participant_cap": 10,
        "questions": [
            {
                "type": "rating_scale",
                "prompt": "How was this sprint overall?",
                "position": 1,
                # Fixed: Changed from min_value/max_value to min/max
                "sub_question": {"min": 1, "max": 5},
            },
            {
                "type": "long_answer",
                "prompt": "What went well?",
                "position": 2,
                # Fixed: Added required max_length constraint
                "sub_question": {"max_length": 500},
            },
            {
                "type": "multiple_choice",
                "prompt": "What should we focus on next sprint?",
                "position": 3,
                # Fixed: Align with whatever layout MultipleChoiceQuestionIn uses.
                # If it mirrors MultipleChoiceQuestionOut, it should look like this:
                "sub_question": {
                    "option_1": "Testing",
                    "option_2": "Tech debt",
                    "option_3": "Docs",
                    "option_4": None,
                    "allow_multiple": False,
                },
            },
        ],
    }
