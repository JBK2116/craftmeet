#!/usr/bin/env python3
"""
Craftmeet host driver for k6 WebSocket load tests.

Connects to the meeting as host via WebSocket, starts the meeting, and
optionally cycles through questions / reveals.  Keeps the connection
alive so that participant VUs can connect and exchange messages.

Usage (separate terminal, before or alongside k6)::

    cd backend
    python k6/host-driver.py [--no-auto] [--base-url ws://localhost:8000]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
from pathlib import Path

import httpx
import websockets

# Ensure backend is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

TEST_DATA_FILE = Path(__file__).resolve().parent / "test-data.json"


# Helpers
def _load_test_data() -> dict:
    if not TEST_DATA_FILE.exists():
        print(f"{TEST_DATA_FILE} not found. Run setup.py first.")
        sys.exit(1)
    return json.loads(TEST_DATA_FILE.read_text())


def _build_ws_url(base_url: str, meeting_id: str, role: str) -> str:
    """Build a full WebSocket URL for the given role."""
    base = base_url.replace("http://", "ws://").replace("https://", "wss://")
    base = base.rstrip("/")
    # If base_url includes /api/v1, strip it; we add the full path ourselves
    if base.endswith("/api/v1"):
        base = base[: -len("/api/v1")]
    return f"{base}/api/v1/meetings/{meeting_id}/{role}/ws"


# Host flow
async def host_flow(base_url: str, auto: bool, duration: int = 120) -> None:
    data = _load_test_data()
    meeting_id = data["meeting_id"]
    questions = data.get("questions", [])
    host_cookie = data["host_cookie"]

    ws_url = _build_ws_url(base_url, meeting_id, "host")

    print("=== Host driver ===")
    print(f"  Meeting: {meeting_id}")
    print(f"  WS URL:  {ws_url}")
    print(f"  Auto:    {auto}")
    print()

    # Connect
    async with websockets.connect(
        ws_url,
        additional_headers={"Cookie": host_cookie},
        max_size=2**20,
    ) as ws:
        print("Connected as host")

        if not auto:
            print("  (--no-auto) Keeping room open — press Ctrl+C to stop.")
            # Just keep the connection alive
            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    parsed = json.loads(msg)
                    print(f"  ← {parsed['type']}")
            except TimeoutError:
                pass
            except asyncio.CancelledError:
                pass
            return

        # Auto-pilot mode
        print("  Auto-pilot: starting meeting …")

        # Use the first question as the starter
        if not questions:
            print("  ✗ No questions in test data — falling back to --no-auto")
            await asyncio.sleep(float(duration))
            return

        # We need the actual question data (with sub_question.id).
        # Fetch the meeting details via REST to get the full question objects.
        async with httpx.AsyncClient(
            cookies={"access_token": data["host_token"]},
            timeout=httpx.Timeout(10.0),
        ) as http:
            resp = await http.get(f"{base_url}/meetings/{meeting_id}")
            if resp.status_code != 200:
                print(f"  ✗ Failed to fetch meeting: {resp.status_code}")
                return
            full_meeting = resp.json()

        full_questions = full_meeting.get("questions", [])
        if not full_questions:
            print("  ✗ No questions on meeting — falling back to --no-auto")
            await asyncio.sleep(float(duration))
            return

        print(f"  Got {len(full_questions)} question(s) from API")

        # Start meeting (sends first question)
        first_q = full_questions[0]
        await ws.send(
            json.dumps(
                {
                    "type": "meeting_started",
                    "payload": {"question": first_q},
                }
            )
        )
        print(f"  → meeting_started (question: {first_q['id']})")

        last_action = asyncio.get_event_loop().time()

        # Event loop
        async def recv_loop():
            nonlocal last_action
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    msg = json.loads(raw)
                    last_action = asyncio.get_event_loop().time()
                    if msg["type"] in (
                        "response_received",
                        "participant_connected",
                        "participant_disconnected",
                    ):
                        # High-volume messages — print summary
                        pass  # too noisy
                    else:
                        print(f"  ← {msg['type']}")
                except TimeoutError:
                    continue
                except websockets.ConnectionClosed:
                    print("  ✗ Connection closed by server")
                    break

        recv_task = asyncio.create_task(recv_loop())

        try:
            # Wait a few seconds for participants to join and respond
            await asyncio.sleep(8.0)

            # Reveal responses
            await ws.send(json.dumps({"type": "reveal"}))
            print("  → reveal")

            await asyncio.sleep(5.0)

            # Advance through remaining questions
            for q in full_questions[1:]:
                await ws.send(
                    json.dumps(
                        {
                            "type": "next_question",
                            "payload": {"question": q},
                        }
                    )
                )
                print(f"  → next_question ({q['id']})")
                await asyncio.sleep(8.0)

                await ws.send(json.dumps({"type": "reveal"}))
                print("  → reveal")
                await asyncio.sleep(5.0)

            # Wait for any final messages
            print("  Auto-pilot complete — keeping room open …")
            await asyncio.sleep(float(duration))

        finally:
            recv_task.cancel()
            try:
                await recv_task
            except asyncio.CancelledError:
                pass

            # End meeting
            print("  → meeting_ended")
            try:
                await ws.send(
                    json.dumps(
                        {
                            "type": "meeting_ended",
                        }
                    )
                )
            except websockets.ConnectionClosed:
                pass

        print("✓ Host disconnected")


# Main
async def main():
    parser = argparse.ArgumentParser(description="Craftmeet host driver for k6 tests")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000/api/v1",
        help="REST base URL of the backend (default: http://localhost:8000/api/v1)",
    )
    parser.add_argument(
        "--no-auto",
        action="store_true",
        help="Just open the room; do not auto-pilot questions",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=120,
        help="Extra idle time after auto-pilot completes (seconds, default: 120)",
    )
    args = parser.parse_args()

    stop = asyncio.Event()

    def _sig_handler():
        print("\n  Interrupted — shutting down.")
        stop.set()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, _sig_handler)
    loop.add_signal_handler(signal.SIGTERM, _sig_handler)

    try:
        await host_flow(args.base_url, not args.no_auto, args.duration)
    except Exception as e:
        print(f"✗ Fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
