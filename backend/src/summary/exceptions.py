from src.exceptions import BaseError


class MeetingNotEndedError(BaseError):
    """Meeting has not ended yet"""

    def __init__(self, m_id: str | None = None):
        if m_id:
            super().__init__(f"meeting with id: {m_id} has not ended")
        else:
            super().__init__("meeting not ended")


class OpenAiError(BaseError):
    """OpenAI error during request"""

    def __init__(self):
        super().__init__("error summarizing meeting with openai")


class PdfGenerationError(BaseError):
    """Error during PDF generation"""

    def __init__(self):
        super().__init__("error generating pdf summary for meeting")
