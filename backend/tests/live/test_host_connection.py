"""Host connect / reconnect / stale-host takeover / disconnect."""

import asyncio

import pytest
from sqlalchemy import select

from src.models import Meeting, User
from src.types import MeetingStatus
from tests.live.builders import chat, question_out, yes_no_response


async def _fresh(session, model, pk):
    """Re-read a row, bypassing the identity map (other sessions wrote it)."""
    result = await session.execute(
        select(model).where(model.id == pk).execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def test_first_host_connect_marks_meeting_live(live, meeting, host_user, session):
    await live.connect_host()

    db_meeting = await _fresh(session, Meeting, meeting.id)
    db_user = await _fresh(session, User, host_user.id)
    assert db_meeting.status == MeetingStatus.LIVE
    assert db_user.live_meeting is True


async def test_second_host_is_rejected_while_first_is_connected(live):
    first = await live.connect_host()
    second = await live.connect_host(ready=False)

    closed = await second.wait_closed()
    assert closed.code == 1008
    assert closed.reason == "A host is already connected to the live meeting"
    # the incumbent was probed with a verification message and stays connected
    await first.wait_for("__host_verify")
    await first.assert_still_open()


async def test_host_disconnect_is_broadcast_to_participants(live):
    host = await live.connect_host()
    p = await live.join("alice")

    await host.close()

    await p.wait_for("host_disconnected")


async def test_host_reconnect_after_disconnect_replays_state(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    question = question_out(meeting.id)
    await host.send("meeting_started", {"question": question})
    await alice.wait_for("meeting_started")
    await alice.send("response_received", yes_no_response(question, alice.pid))
    await host.wait_for("response_received")
    await alice.send("chat_received", chat(u_id=alice.pid, name="alice", message="hi"))
    await host.wait_for("chat_received")
    await host.close()
    await alice.wait_for("host_disconnected")

    host2 = await live.connect_host(ready=False)

    state = await host2.wait_for_payload("meeting_state")
    assert state["question"]["id"] == question["id"]
    assert state["started_at"] is not None
    assert [r["participant_id"] for r in state["responses"]] == [str(alice.pid)]
    assert [
        (p["id"], p["username"], p["has_answered"]) for p in state["participants"]
    ] == [(str(alice.pid), "alice", True)]
    chats = await host2.wait_for_payload("chat_state")
    assert [c["message"] for c in chats["chats"]] == ["hi"]
    await alice.wait_for("host_reconnected")


async def test_host_reconnect_without_chat_sends_no_chat_state(live):
    host = await live.connect_host()
    await host.close()

    host2 = await live.connect_host(ready=False)

    await host2.wait_for("meeting_state")
    await host2.assert_not_received("chat_state")


async def test_stale_host_connection_is_taken_over(live):
    host = await live.connect_host()
    p = await live.join("alice")
    live.break_connection(host)  # socket is dead but no disconnect was observed

    host2 = await live.connect_host(ready=False)

    await host2.wait_for("meeting_state")
    await p.wait_for("host_reconnected")
    await host2.assert_still_open()


async def test_meeting_state_for_reconnecting_host_before_start(live):
    host = await live.connect_host()
    await host.close()

    host2 = await live.connect_host(ready=False)

    state = await host2.wait_for_payload("meeting_state")
    assert state == {
        "question": None,
        "responses": [],
        "participants": [],
        "started_at": None,
    }


async def test_host_ping_gets_no_pong(live):
    host = await live.connect_host()

    await host.send("ping")

    await host.assert_not_received("pong")


@pytest.mark.expects_server_error
async def test_malformed_host_message_closes_with_internal_error(live):
    """Characterization: an unknown message type is not handled gracefully.

    ``WebIn`` validation errors escape the receive loop, so the ASGI app
    raises and the client sees an internal-error close (1011).
    """
    host = await live.connect_host()

    await host.send("no_such_message")

    closed = await host.wait_closed()
    assert closed.code == 1011
    assert len(live.server_errors) == 1


async def test_invalid_json_from_host_does_not_crash_the_server(live):
    host = await live.connect_host()

    await host.send_text("this is not json")
    await asyncio.sleep(0.2)

    assert live.server_errors == []
