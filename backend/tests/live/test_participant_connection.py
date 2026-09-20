"""Participant connect / lobby / reconnect / cap / heartbeat / disconnect."""

import uuid

import pytest

from tests.live.builders import chat, question_out


async def test_participant_without_a_room_is_rejected_meeting_not_found(live):
    p = await live.connect_participant()

    closed = await p.wait_closed()
    assert (closed.code, closed.reason) == (4001, "meeting not found")


async def test_participant_connected_enters_lobby_and_host_is_told(live):
    host = await live.connect_host()
    pid = uuid.uuid4()

    p = await live.lobby(pid)

    lobby_entry = {
        "id": str(pid),
        "username": None,
        "connected": True,
        "has_answered": False,
        "is_lobby": True,
    }
    assert await host.wait_for_payload("participant_connected") == lobby_entry
    state = await p.wait_for_payload("participants_state")
    assert state["participants"] == [lobby_entry]


async def test_participant_state_payload_for_new_participant(live):
    await live.connect_host()
    pid = uuid.uuid4()
    p = await live.connect_participant(pid)

    await p.send("participant_connected", {"meeting_id": str(live.meeting_id)})

    assert await p.wait_for_payload("participant_state") == {
        "id": str(pid),
        "username": None,
        "connected": True,
        "has_answered": False,
        "is_lobby": True,
    }
    # nothing to replay yet
    await p.assert_not_received("current_question")
    await p.assert_not_received("chat_state")
    await p.assert_not_received("reveal")


async def test_late_participant_gets_current_question_replayed(live, meeting):
    host = await live.connect_host()
    question = question_out(meeting.id)
    await host.send("meeting_started", {"question": question})
    await live.host_barrier(host)  # meeting_started has been processed

    p = await live.lobby()

    payload = await p.wait_for_payload("current_question")
    assert payload["question"]["id"] == question["id"]
    await p.assert_not_received("reveal")


async def test_chat_history_is_replayed_to_connecting_participant(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    await alice.send("chat_received", chat(u_id=alice.pid, name="alice", message="one"))
    await host.wait_for("chat_received")

    bob = await live.lobby()

    payload = await bob.wait_for_payload("chat_state")
    assert [c["message"] for c in payload["chats"]] == ["one"]


async def test_participant_disconnect_is_reported_to_host(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.wait_for("participant_connected")

    await alice.close()

    payload = await host.wait_for_payload("participant_disconnected")
    assert payload == {"id": str(alice.pid)}


async def test_disconnected_participant_stays_listed_as_disconnected(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    await alice.close()
    await host.wait_for("participant_disconnected")
    await host.close()

    host2 = await live.connect_host(ready=False)

    state = await host2.wait_for_payload("meeting_state")
    assert [(p["username"], p["connected"]) for p in state["participants"]] == [
        ("alice", False)
    ]


async def test_participant_reconnect_gets_state_and_old_socket_is_closed(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.wait_for("participant_connected")

    alice2 = await live.connect_participant(alice.pid)
    await alice2.send("participant_connected", {"meeting_id": str(live.meeting_id)})

    closed = await alice.wait_closed()
    assert closed.code == 1008
    assert closed.reason == (
        "A participant has reconnected to this meeting on a new websocket"
    )
    # the participant keeps their name and lobby status across the reconnect
    state = await alice2.wait_for_payload("participant_state")
    assert (state["username"], state["is_lobby"], state["connected"]) == (
        "alice",
        False,
        True,
    )
    payload = await host.wait_for_payload(
        "participant_connected", where=lambda m: m["payload"]["connected"]
    )
    assert payload["id"] == str(alice.pid)


async def test_ping_gets_pong(live):
    await live.connect_host()
    p = await live.connect_participant()

    await p.send("ping")

    assert (await p.wait_for("pong")) == {"type": "pong"}


async def test_ping_is_answered_before_participant_registers(live):
    await live.connect_host()
    p = await live.connect_participant()
    await p.send("ping")
    await p.wait_for("pong")
    await p.assert_still_open()


@pytest.mark.expects_server_error  # current impl re-enters receive_json after closing
async def test_participant_message_for_ended_room_closes_normally(live, meeting):
    host = await live.connect_host()
    p = await live.join("alice")
    await host.send("meeting_started", {"question": question_out(meeting.id)})
    await p.wait_for("meeting_started")
    await host.send("meeting_ended")
    await p.wait_for("meeting_ended")

    await p.send("participant_connected", {"meeting_id": str(live.meeting_id)})

    closed = await p.wait_closed()
    assert (closed.code, closed.reason) == (1000, "meeting room not found or ended")


# cap
async def test_participant_cap_rejects_extra_participants(live, make_meeting):
    meeting = await make_meeting(participant_cap=2)
    await live.connect_host(meeting_id=meeting.id)
    await live.join("alice", meeting_id=meeting.id)
    await live.lobby(meeting_id=meeting.id)  # a connected lobby user counts too

    extra = await live.connect_participant(meeting_id=meeting.id)

    closed = await extra.wait_closed()
    assert (closed.code, closed.reason) == (4003, "meeting is full")


async def test_participant_at_cap_can_reconnect(live, make_meeting):
    meeting = await make_meeting(participant_cap=1)
    await live.connect_host(meeting_id=meeting.id)
    alice = await live.join("alice", meeting_id=meeting.id)

    alice2 = await live.connect_participant(alice.pid, meeting_id=meeting.id)

    await alice2.assert_still_open()
    await alice2.send("participant_connected", {"meeting_id": str(meeting.id)})
    await alice2.wait_for("participant_state")


async def test_named_participant_keeps_their_cap_slot_after_disconnecting(
    live, make_meeting
):
    meeting = await make_meeting(participant_cap=1)
    host = await live.connect_host(meeting_id=meeting.id)
    alice = await live.join("alice", meeting_id=meeting.id)
    await alice.close()
    await host.wait_for("participant_disconnected")

    bob = await live.connect_participant(meeting_id=meeting.id)

    assert (await bob.wait_closed()).code == 4003


async def test_lobby_participant_frees_their_cap_slot_after_disconnecting(
    live, make_meeting
):
    meeting = await make_meeting(participant_cap=1)
    host = await live.connect_host(meeting_id=meeting.id)
    ghost = await live.lobby(meeting_id=meeting.id)
    await ghost.close()
    await host.wait_for("participant_disconnected")

    bob = await live.lobby(meeting_id=meeting.id)

    await bob.assert_still_open()
