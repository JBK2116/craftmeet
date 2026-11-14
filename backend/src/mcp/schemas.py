"""MCP-specific schemas for request and response payloads."""

import datetime
import uuid

from pydantic import BaseModel, Field

from src.types import MeetingStatus


class MeetingSummary(BaseModel):
    """Lightweight summary of a meeting returned by the list_meetings tool."""

    id: uuid.UUID
    title: str
    status: MeetingStatus
    room_code: str
    created_at: datetime.datetime
    question_count: int
    url: str


class ListMeetingsResponse(BaseModel):
    """Response returned by the list_meetings MCP tool."""

    meetings: list[MeetingSummary] = Field(
        description="List of meetings associated with the user."
    )
    total_returned: int = Field(
        description="Number of meetings returned in the current response."
    )
    has_more: bool = Field(
        description="Indicates if there are more meetings available for pagination."
    )
    next_offset: int | None = Field(
        description="The offset to use for the next page of results, if any."
    )
