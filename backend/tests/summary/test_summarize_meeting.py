from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient

from src.exceptions import DatabaseError
from src.models import Meeting
from src.summary.exceptions import (
    CSVGenerationError,
    OpenAiError,
    PdfGenerationError,
)

SUMMARY_URL = "/meetings/{meeting_id}/summary"


# Success paths


async def test_summary_csv_success(
    authenticated_client: AsyncClient, completed_meeting: Meeting
) -> None:
    """Completed meeting + csv export -> 200 text/csv file response."""
    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "csv"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")


async def test_summary_csv_content(
    authenticated_client: AsyncClient, completed_meeting_with_responses: Meeting
) -> None:
    """CSV body contains the header row and one row per response."""
    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting_with_responses.id),
        params={"export": "csv"},
    )
    assert response.status_code == 200
    body = response.text
    assert "question_id" in body
    assert "answer" in body
    assert "yes" in body
    assert "no" in body


async def test_summary_pdf_success(
    authenticated_client: AsyncClient,
    completed_meeting: Meeting,
    mock_ai_summary: AsyncMock,
) -> None:
    """Completed meeting + pdf export -> 200 application/pdf, AI called once."""
    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "pdf"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content[:4] == b"%PDF"
    mock_ai_summary.assert_awaited_once()


# Authentication


async def test_summary_missing_access_token(
    client: AsyncClient, completed_meeting: Meeting
) -> None:
    """No access token cookie sent -> 401."""
    response = await client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "csv"},
    )
    assert response.status_code == 401


async def test_summary_invalid_access_token(
    client: AsyncClient, completed_meeting: Meeting
) -> None:
    """Malformed access token -> 401."""
    client.cookies.set("access_token", "sndkjgnqiugoinweogqgenoiq")
    response = await client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "csv"},
    )
    assert response.status_code == 401


async def test_summary_expired_access_token(
    client: AsyncClient,
    expired_access_token_jwt: str,
    completed_meeting: Meeting,
) -> None:
    """Expired access token -> 401."""
    client.cookies.set("access_token", expired_access_token_jwt)
    response = await client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "csv"},
    )
    assert response.status_code == 401


async def test_summary_orphan_access_token(
    client: AsyncClient,
    orphan_access_token_jwt: str,
    completed_meeting: Meeting,
) -> None:
    """Valid JWT for a non-existent user -> 401."""
    client.cookies.set("access_token", orphan_access_token_jwt)
    response = await client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "csv"},
    )
    assert response.status_code == 401


# Validation and state errors


async def test_summary_meeting_not_found(
    authenticated_client: AsyncClient, non_existent_meeting_id
) -> None:
    """Meeting id that does not exist -> 404."""
    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=non_existent_meeting_id),
        params={"export": "csv"},
    )
    assert response.status_code == 404


async def test_summary_meeting_not_ended(
    authenticated_client: AsyncClient, live_meeting: Meeting
) -> None:
    """Meeting not yet COMPLETED -> 400."""
    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=live_meeting.id),
        params={"export": "csv"},
    )
    assert response.status_code == 400


async def test_summary_invalid_export(
    authenticated_client: AsyncClient, completed_meeting: Meeting
) -> None:
    """Unsupported export type -> 422."""
    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "docx"},
    )
    assert response.status_code == 422
    assert response.json()["type"] == "export"


# Server errors
async def test_summary_openai_error(
    authenticated_client: AsyncClient,
    completed_meeting: Meeting,
    monkeypatch,
) -> None:
    """AI summarization failure -> 500."""
    monkeypatch.setattr(
        "src.summary.service._get_ai_summary",
        AsyncMock(side_effect=OpenAiError()),
    )
    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "pdf"},
    )
    assert response.status_code == 500


async def test_summary_pdf_generation_error(
    authenticated_client: AsyncClient,
    completed_meeting: Meeting,
    mock_ai_summary: AsyncMock,
    monkeypatch,
) -> None:
    """PDF generation failure -> 500."""
    monkeypatch.setattr(
        "src.summary.service.generate_pdf",
        MagicMock(side_effect=PdfGenerationError()),
    )
    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "pdf"},
    )
    assert response.status_code == 500


async def test_summary_csv_generation_error(
    authenticated_client: AsyncClient,
    completed_meeting: Meeting,
    monkeypatch,
) -> None:
    """CSV generation failure -> 500."""
    monkeypatch.setattr(
        "src.summary.service.generate_csv",
        MagicMock(side_effect=CSVGenerationError()),
    )
    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "csv"},
    )
    assert response.status_code == 500


async def test_summary_database_error(
    authenticated_client: AsyncClient,
    completed_meeting: Meeting,
    monkeypatch,
) -> None:
    """Database failure -> 500."""
    monkeypatch.setattr(
        "src.summary.service.get_meeting",
        AsyncMock(side_effect=DatabaseError("database error occurred")),
    )
    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "csv"},
    )
    assert response.status_code == 500


# Existing file short-circuit
async def test_summary_pdf_uses_existing_file(
    authenticated_client: AsyncClient,
    completed_meeting: Meeting,
    mock_ai_summary: AsyncMock,
    tmp_path: Path,
) -> None:
    """An existing PDF on disk is returned without calling AI."""
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_bytes = b"%PDF-1.4 existing"
    (pdf_dir / f"{completed_meeting.id}.pdf").write_bytes(pdf_bytes)

    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "pdf"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content == pdf_bytes
    mock_ai_summary.assert_not_called()


async def test_summary_csv_uses_existing_file(
    authenticated_client: AsyncClient,
    completed_meeting: Meeting,
    tmp_path: Path,
) -> None:
    """An existing CSV on disk is returned without regenerating."""
    csv_dir = tmp_path / "csvs"
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_bytes = b"question_id,question_type\n"
    (csv_dir / f"{completed_meeting.id}.csv").write_bytes(csv_bytes)

    response = await authenticated_client.post(
        SUMMARY_URL.format(meeting_id=completed_meeting.id),
        params={"export": "csv"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.content == csv_bytes
