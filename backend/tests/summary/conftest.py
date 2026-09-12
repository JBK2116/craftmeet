"""Summary-specific fixtures for the meeting summary endpoint tests.

The summary endpoint is nested under ``/meetings``, so the user/meeting
fixtures from ``tests.meeting.conftest`` are reused directly rather than
redefined here.
"""

import datetime
import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.auth.token import generate_access_token
from src.models import (
    Meeting,
    Question,
    Stat,
    User,
    YesNoQuestion,
    YesNoResponse,
)
from src.types import MeetingStatus, QuestionType
from tests.meeting.conftest import (
    completed_meeting,
    expired_access_token_jwt,
    live_meeting,
    non_existent_meeting_id,
    orphan_access_token_jwt,
    verified_meeting_user,
)

__all__ = [
    "authenticated_client",
    "completed_meeting",
    "expired_access_token_jwt",
    "live_meeting",
    "non_existent_meeting_id",
    "orphan_access_token_jwt",
    "verified_meeting_user",
]


@pytest_asyncio.fixture
async def authenticated_client(
    client: AsyncClient, verified_meeting_user: User
) -> AsyncClient:
    """Return an HTTP client with a valid access token for ``verified_meeting_user``.

    Mints the access token directly rather than logging in via ``/auth/login``,
    which is rate-limited and would throttle the suite after enough tests.
    """
    token = generate_access_token(u_id=verified_meeting_user.id)
    client.cookies.set("access_token", token)
    return client


@pytest.fixture(autouse=True)
def _isolate_summary_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect PDF/CSV storage to a temp dir.

    ``service.py`` reads ``PDF_DIR``/``CSV_DIR`` (imported from ``save``)
    and ``save.py`` uses its own module-level copies, so both must be
    patched to avoid writing real files into ``backend/storage``.
    """
    pdf_dir = tmp_path / "pdfs"
    csv_dir = tmp_path / "csvs"
    monkeypatch.setattr("src.summary.service.PDF_DIR", pdf_dir)
    monkeypatch.setattr("src.summary.service.CSV_DIR", csv_dir)
    monkeypatch.setattr("src.summary.save.PDF_DIR", pdf_dir)
    monkeypatch.setattr("src.summary.save.CSV_DIR", csv_dir)


@pytest_asyncio.fixture
async def completed_meeting_with_responses(session, verified_meeting_user) -> Meeting:
    """A COMPLETED meeting with one yes/no question and two responses."""
    meeting = Meeting(
        user_id=verified_meeting_user.id,
        title="Completed Meeting With Responses",
        description="A completed meeting for summary tests",
        room_code="SUMRESP1",
        duration=15,
        participant_cap=20,
        total_questions=1,
        status=MeetingStatus.COMPLETED,
    )
    session.add(meeting)
    await session.flush()
    await session.refresh(meeting)

    question = Question(
        meeting_id=meeting.id,
        type=QuestionType.YES_NO,
        prompt="Was this useful?",
        position=1,
    )
    session.add(question)
    await session.flush()
    await session.refresh(question)

    sub_question = YesNoQuestion(question_id=question.id)
    session.add(sub_question)
    await session.flush()
    await session.refresh(sub_question)

    now = datetime.datetime.now(tz=datetime.UTC)
    session.add_all(
        [
            YesNoResponse(
                question_id=sub_question.id,
                participant_id=uuid.uuid4(),
                value=True,
                created_at=now,
            ),
            YesNoResponse(
                question_id=sub_question.id,
                participant_id=uuid.uuid4(),
                value=False,
                created_at=now,
            ),
        ]
    )

    session.add(
        Stat(
            meeting_id=meeting.id,
            total_participants=2,
            total_questions_asked=1,
            total_responses_received=2,
            average_response_rate=1.0,
        )
    )
    await session.commit()
    await session.refresh(meeting)
    return meeting


@pytest.fixture
def ai_summary_json() -> str:
    """A valid AI summary JSON matching ``MeetingSummary`` (yes/no question)."""
    return json.dumps(
        {
            "executive_summary": "The meeting went well.",
            "key_takeaways": ["Shipping is on track."],
            "participation_insight": "Everyone engaged.",
            "questions": [
                {
                    "position": 1,
                    "prompt": "Was this useful?",
                    "type": "yes_no",
                    "response_count": 2,
                    "response_rate": 100.0,
                    "headline": "Half found it useful.",
                    "narrative": "One yes and one no.",
                    "details": {
                        "yes_count": 1,
                        "no_count": 1,
                        "yes_pct": 50.0,
                        "no_pct": 50.0,
                    },
                }
            ],
        }
    )


@pytest.fixture
def mock_ai_summary(monkeypatch: pytest.MonkeyPatch, ai_summary_json: str) -> AsyncMock:
    """Replace ``service._get_ai_summary`` with a mock returning canned JSON."""
    mock = AsyncMock(return_value=ai_summary_json)
    monkeypatch.setattr("src.summary.service._get_ai_summary", mock)
    return mock
