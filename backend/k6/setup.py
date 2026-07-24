#!/usr/bin/env python3
"""
k6 WebSocket test data setup.

Creates all the data needed for k6 load tests against the live-meeting
WebSocket endpoints:

  1. A verified user (direct DB insert — bypasses signup/verify email flow)
  2. An access-token JWT for the host
  3. A meeting with questions (via the REST API, authenticated with the JWT)
  4. N participant join-tokens (via POST /meetings/join)

Outputs ``test-data.json`` in the same directory, which the k6 scripts read.

Usage::

    cd backend
    python k6/setup.py [--participants 50] [--base-url http://localhost:8000/api/v1]

Requires the backend and PostgreSQL to be running (``docker compose up`` or
``uvicorn``).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure the backend package is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from src.auth.crypto import hash_password  # noqa: E402
from src.auth.token import (  # noqa: E402
    generate_access_token,
    generate_participants_meeting_access_token,
)
from src.config import get_settings  # noqa: E402
from src.constants import (  # noqa: E402
    PARTICIPANT_COOKIE_BUFFER_SECONDS,
)
from src.database import DATABASE_URL  # noqa: E402

# Constants

VALID_PASSWORD = "k6TestP@ss1!"  # noqa: S105
TEST_EMAIL = "k6-load-test@craftmeet.local"
TEST_USERNAME = "k6host"

MEETING_PAYLOAD: dict[str, Any] = {
    "title": "K6 Load Test Meeting",
    "description": "Auto-generated for k6 WebSocket load testing",
    "participant_cap": 100,
    "duration": 30,
    "questions": [
        {
            "type": "yes_no",
            "prompt": "Is the WebSocket connection stable?",
            "position": 1,
            "sub_question": {},
        },
        {
            "type": "rating_scale",
            "prompt": "Rate the connection quality",
            "position": 2,
            "sub_question": {"min": 1, "max": 5},
        },
    ],
}

OUTPUT_FILE = Path(__file__).resolve().parent / "test-data.json"


# Helpers
async def _ensure_user(engine) -> uuid.UUID:
    """
    Insert a verified test user via the ORM.
    If the email already exists the existing user ID is returned.
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from src.models import User

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with maker() as session:
        # Check if the user already exists from a previous run
        result = await session.execute(select(User.id).where(User.email == TEST_EMAIL))
        existing = result.scalar_one_or_none()
        if existing is not None:
            print(f"  ↳ User already exists: {existing}")
            return existing

        now = datetime.datetime.now(tz=datetime.UTC)
        user = User(
            email=TEST_EMAIL,
            username=TEST_USERNAME,
            password=hash_password(VALID_PASSWORD),
            verified=True,
            verified_at=now,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"  ↳ Created user: {user.id}")
        return user.id


def _make_host_token(user_id: uuid.UUID) -> str:
    """Generate a signed access-token JWT for the host."""
    return generate_access_token(u_id=user_id)


async def _create_meeting(client: httpx.AsyncClient, base_url: str) -> dict[str, Any]:
    """Create a meeting via the REST API.  Returns the parsed JSON body."""
    resp = await client.post(
        f"{base_url}/meetings",
        json=MEETING_PAYLOAD,
    )
    if resp.status_code != 201:
        print(f" Meeting creation failed ({resp.status_code}): {resp.text}")
        sys.exit(1)
    meeting = resp.json()
    print(f" Created meeting: {meeting['id']}  (code: {meeting['room_code']})")
    return meeting


def _generate_participant_token(
    meeting_id: uuid.UUID,
    duration_minutes: int,
    index: int,
) -> dict[str, str]:
    """Generate a participant JWT and return {id, token, cookie_name, username}.

    Bypasses the rate-limited POST /meetings/join endpoint by calling the
    same token-generation function the app uses internally.
    """
    p_id = uuid.uuid4()
    username = f"k6user{index:04d}"
    duration_seconds = duration_minutes * 60 + PARTICIPANT_COOKIE_BUFFER_SECONDS
    token = generate_participants_meeting_access_token(
        duration=duration_seconds,
        m_id=meeting_id,
        p_id=p_id,
    )
    cookie_name = f"participants_meeting_access_token_{meeting_id}"
    return {
        "id": str(p_id),
        "username": username,
        "token": token,
        "cookie_name": cookie_name,
    }


# Main
async def main(participant_count: int, base_url: str) -> None:
    settings = get_settings()  # noqa: F841
    print("=== Craftmeet k6 Setup ===\n")

    print("[1/4] Ensuring test user exists …")
    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        user_id = await _ensure_user(engine)
    finally:
        await engine.dispose()

    print("[2/4] Generating host access token …")
    host_token = _make_host_token(user_id)
    print(f"  ↳ Host token: {host_token[:20]}…")

    print("[3/4] Creating meeting …")
    async with httpx.AsyncClient(
        cookies={"access_token": host_token},
        timeout=httpx.Timeout(10.0),
    ) as client:
        meeting = await _create_meeting(client, base_url)
        meeting_id = meeting["id"]
        room_code = meeting["room_code"]

        # Fetch full meeting to get question IDs (needed by k6 auto-responder)
        resp = await client.get(f"{base_url}/meetings/{meeting_id}")
        if resp.status_code != 200:
            print(f"  ✗ Failed to fetch full meeting: {resp.status_code}")
            sys.exit(1)
        full_meeting = resp.json()
        questions = [
            {
                "id": q["id"],
                "type": q["type"],
                "sub_question_id": q["sub_question"]["id"],
            }
            for q in full_meeting.get("questions", [])
        ]
        print(f"Questions: {len(questions)} loaded")

        print(f"[4/4] Generating {participant_count} participant tokens …")
        participants: list[dict[str, str]] = [
            _generate_participant_token(
                meeting_id=meeting_id,
                duration_minutes=MEETING_PAYLOAD["duration"],
                index=i,
            )
            for i in range(participant_count)
        ]
        print(f"  ↳ {len(participants)} participant tokens generated")

    # 5. Write output
    output: dict[str, Any] = {
        "base_url": base_url,
        # host
        "host_token": host_token,
        "host_cookie": f"access_token={host_token}",
        # meeting
        "meeting_id": meeting_id,
        "room_code": room_code,
        "questions": questions,
        # participants
        "participant_count": len(participants),
        "participants": participants,
    }

    OUTPUT_FILE.write_text(json.dumps(output, indent=2))
    print(f"\n Wrote {OUTPUT_FILE}")
    print("  Run the k6 test with:\n    k6 run k6/participant-load-test.js")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="k6 WebSocket test data setup")
    parser.add_argument(
        "--participants",
        type=int,
        default=100,
        help="Number of participant tokens to generate (default: 100)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000/api/v1",
        help="Base URL of the running backend (default: http://localhost:8000/api/v1)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.participants, args.base_url))
