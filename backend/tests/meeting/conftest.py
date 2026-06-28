"""Meeting-specific fixtures for CRUD tests.

Provides a verified user, an authenticated HTTP client, and valid
meeting-creation payloads covering the various question types.
"""

import datetime
import uuid
from typing import Any

import jwt as pyjwt
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.crypto import hash_password
from src.auth.token import JWT_ALGORITHM, generate_access_token
from src.config import get_settings
from src.models import Meeting, Question, Stat, User, YesNoQuestion
from src.types import QuestionType

VALID_PASSWORD = "ExistingP@ss1"  # noqa: S105


@pytest_asyncio.fixture
async def verified_meeting_user(session: AsyncSession) -> User:
    """A verified user for meeting tests.

    Uses a distinct email so it doesn't collide with auth-conftest
    fixtures when both are imported in the same module.
    """
    user = User(
        email="meeting-test@example.com",
        username="meetingtest",
        password=hash_password(VALID_PASSWORD),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def expired_access_token_jwt(verified_meeting_user: User) -> str:
    """An access token JWT for ``verified_user`` whose ``exp`` is in the past.

    ``decode_access_token`` will raise ``InvalidTokenError`` because the
    signature-verification step detects the expired ``exp`` claim.
    """
    settings = get_settings()
    now = datetime.datetime.now(datetime.UTC)
    payload = {
        "user_id": str(verified_meeting_user.id),
        "exp": now - datetime.timedelta(minutes=1),
        "iat": now - datetime.timedelta(hours=1),
        "type": "access",
    }
    return pyjwt.encode(
        payload=payload, key=settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
    )


@pytest_asyncio.fixture
async def orphan_access_token_jwt() -> str:
    """A structurally valid access token whose ``user_id`` does **not**
    belong to any user in the database.

    ``decode_access_token`` succeeds, but the subsequent user lookup
    returns ``None``, which triggers ``InvalidTokenError`` in handlers
    like ``handle_me``.
    """
    return generate_access_token(u_id=uuid.uuid4())


@pytest_asyncio.fixture
async def authenticated_client(
    client: AsyncClient, verified_meeting_user: User
) -> AsyncClient:
    """Return an HTTP client with valid ``access_token`` cookie for
    ``meeting_user``.

    Logs in the user via the login endpoint and copies the resulting
    cookies (``access_token``, ``refresh_token``) onto the client so
    subsequent requests pass the ``get_current_user`` dependency.
    """
    response = await client.post(
        "/auth/login",
        json={"email": verified_meeting_user.email, "password": VALID_PASSWORD},
    )
    for key, value in response.cookies.items():
        client.cookies.set(key, value)
    return client


@pytest_asyncio.fixture
async def create_meeting_payload() -> dict[str, Any]:
    """A valid create-meeting payload with a single yes/no question."""
    return {
        "title": "Team Standup",
        "description": "Daily standup meeting",
        "participant_cap": 20,
        "duration": 15,
        "questions": [
            {
                "type": "yes_no",
                "prompt": "Did you complete your tasks?",
                "position": 1,
                "sub_question": {},
            }
        ],
    }


@pytest_asyncio.fixture
async def another_meeting_user(session: AsyncSession) -> User:
    """A second verified user distinct from ``verified_meeting_user`` for ownership tests."""
    user = User(
        email="another-meeting@example.com",
        username="anothermeeting",
        password=hash_password(VALID_PASSWORD),
        verified=True,
        verified_at=datetime.datetime.now(tz=datetime.UTC),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def verified_user_meeting(
    session: AsyncSession, verified_meeting_user: User
) -> Meeting:
    """A meeting persisted in the DB owned by ``verified_meeting_user`` with one yes/no question."""
    meeting = Meeting(
        user_id=verified_meeting_user.id,
        title="Test Meeting",
        description="A meeting for testing",
        room_code="12345678",
        duration=15,
        participant_cap=20,
        total_questions=1,
    )
    session.add(meeting)
    await session.flush()
    await session.refresh(meeting)

    question = Question(
        meeting_id=meeting.id,
        type=QuestionType.YES_NO,
        prompt="Did you complete your tasks?",
        position=1,
    )
    session.add(question)
    await session.flush()
    await session.refresh(question)

    sub_question = YesNoQuestion(question_id=question.id)
    session.add(sub_question)
    await session.flush()

    stat = Stat(meeting_id=meeting.id)
    session.add(stat)
    await session.commit()
    await session.refresh(meeting)
    return meeting


@pytest_asyncio.fixture
async def another_user_meeting(
    session: AsyncSession, another_meeting_user: User
) -> Meeting:
    """A meeting owned by ``another_meeting_user`` for cross-ownership tests."""
    meeting = Meeting(
        user_id=another_meeting_user.id,
        title="Another User's Meeting",
        description="This meeting belongs to someone else",
        room_code="98765432",
        duration=30,
        participant_cap=10,
        total_questions=1,
    )
    session.add(meeting)
    await session.flush()
    await session.refresh(meeting)

    question = Question(
        meeting_id=meeting.id,
        type=QuestionType.YES_NO,
        prompt="Are you done?",
        position=1,
    )
    session.add(question)
    await session.flush()
    await session.refresh(question)

    sub_question = YesNoQuestion(question_id=question.id)
    session.add(sub_question)
    await session.flush()

    stat = Stat(meeting_id=meeting.id)
    session.add(stat)
    await session.commit()
    await session.refresh(meeting)
    return meeting


@pytest_asyncio.fixture
async def non_existent_meeting_id() -> uuid.UUID:
    """A UUID that does not correspond to any meeting in the database."""
    return uuid.uuid4()


@pytest_asyncio.fixture
async def update_meeting_payload() -> dict[str, Any]:
    """A valid update-meeting payload with updated fields and one question (to be inserted as new)."""
    return {
        "title": "Updated Meeting",
        "description": "Updated description",
        "participant_cap": 25,
        "duration": 20,
        "questions": [
            {
                "type": "rating_scale",
                "prompt": "Rate the meeting",
                "position": 1,
                "sub_question": {"min": 1, "max": 5},
            }
        ],
    }


@pytest_asyncio.fixture
async def create_meeting_payload_multiple_questions() -> dict:
    """A create-meeting payload with multiple question types.

    Covers rating-scale, multiple-choice, and long-answer sub-questions
    in a single meeting.
    """
    return {
        "title": "Sprint Retro",
        "description": "End-of-sprint retrospective",
        "participant_cap": 10,
        "duration": 45,
        "questions": [
            {
                "type": "rating_scale",
                "prompt": "Rate the sprint velocity",
                "position": 1,
                "sub_question": {"min": 1, "max": 5},
            },
            {
                "type": "multiple_choice",
                "prompt": "What should we improve?",
                "position": 2,
                "sub_question": {
                    "option_1": "Communication",
                    "option_2": "Planning",
                    "option_3": "Execution",
                    "allow_multiple": True,
                },
            },
            {
                "type": "long_answer",
                "prompt": "Any other feedback?",
                "position": 3,
                "sub_question": {"max_length": 300},
            },
        ],
    }
