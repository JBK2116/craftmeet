import logging
import uuid
from pathlib import Path

from src.summary.exceptions import PdfGenerationError

logger = logging.getLogger(__name__)

# Path: backend/storage/pdfs/{meeting_id}.pdf
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = _BACKEND_ROOT / "storage"
PDF_DIR = STORAGE_DIR / "pdfs"


def save_pdf(meeting_id: uuid.UUID, pdf_bytes: bytes) -> Path:
    """Persist PDF bytes to disk and return the absolute file path.

    Args:
        meeting_id: Meeting UUID used as the filename (``{meeting_id}.pdf``).
        pdf_bytes: The raw PDF content to write.

    Returns:
        Absolute ``Path`` to the saved file.

    Raises:
        PdfGenerationError: If the directory cannot be created or the write fails.
    """
    try:
        PDF_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.exception("failed to create PDF storage directory %s: %s", PDF_DIR, e)
        raise PdfGenerationError from e

    filepath = PDF_DIR / f"{meeting_id}.pdf"
    try:
        filepath.write_bytes(pdf_bytes)
        logger.info("saved PDF to %s (%d bytes)", filepath, len(pdf_bytes))
    except OSError as e:
        logger.exception("failed to write PDF to %s: %s", filepath, e)
        raise PdfGenerationError from e
    return filepath
