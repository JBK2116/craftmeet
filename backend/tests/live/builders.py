"""Builders for wire-format payloads used by the live contract tests."""

import uuid
from typing import Any


def question_out(
    meeting_id: uuid.UUID,
    *,
    type_: str = "yes_no",
    position: int = 1,
    prompt: str = "Do you agree?",
) -> dict[str, Any]:
    """A ``QuestionOut`` as the host frontend sends it in start/next messages."""
    q_id, sub_id = uuid.uuid4(), uuid.uuid4()
    sub: dict[str, Any] = {"id": str(sub_id), "question_id": str(q_id), "responses": []}
    if type_ == "rating_scale":
        sub |= {"min": 1, "max": 5}
    elif type_ == "long_answer":
        sub |= {"max_length": 200}
    return {
        "id": str(q_id),
        "meeting_id": str(meeting_id),
        "type": type_,
        "prompt": prompt,
        "position": position,
        "status": "open",
        "sub_question": sub,
    }


def yes_no_response(
    question: dict[str, Any], participant_id: uuid.UUID, value: bool = True
) -> dict[str, Any]:
    return {
        "response": {
            "type": "yes_no",
            "question_id": question["sub_question"]["id"],
            "participant_id": str(participant_id),
            "value": value,
        }
    }


def rating_response(
    question: dict[str, Any], participant_id: uuid.UUID, value: int = 3
) -> dict[str, Any]:
    return {
        "response": {
            "type": "rating_scale",
            "question_id": question["sub_question"]["id"],
            "participant_id": str(participant_id),
            "value": value,
        }
    }


def chat(
    *,
    u_id: uuid.UUID,
    message: str = "hello",
    name: str = "someone",
    is_host: bool = False,
) -> dict[str, Any]:
    return {
        "chat": {
            "name": name,
            "u_id": str(u_id),
            "message": message,
            "is_host": is_host,
        }
    }


def new_question_in(position: int = 2) -> dict[str, Any]:
    """Payload of ``add_question`` (a ``QuestionIn``)."""
    return {
        "question": {
            "type": "yes_no",
            "prompt": "Added mid-meeting?",
            "position": position,
            "sub_question": {},
        }
    }
