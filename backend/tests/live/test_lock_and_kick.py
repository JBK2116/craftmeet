"""Lock/unlock (with rejoin bypass), kick and block."""

import uuid


# lock
async def test_lock_and_unlock_are_broadcast_to_participants_not_host(live):
    host = await live.connect_host()
    alice = await live.join("alice")

    await host.send("lock_meeting")
    await alice.wait_for("lock_room_success")
    await host.send("unlock_meeting")
    await alice.wait_for("unlock_room_success")

    # characterization: the *_success acks go to participants only
    await host.assert_not_received("lock_room_success")
    await host.assert_not_received("unlock_room_success")


async def test_lock_is_idempotent(live):
    host = await live.connect_host()
    alice = await live.join("alice")

    await host.send("lock_meeting")
    await host.send("lock_meeting")

    await alice.wait_for("lock_room_success")
    await alice.wait_for("lock_room_success")


async def test_registered_participant_can_rejoin_a_locked_room(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("lock_meeting")
    await alice.wait_for("lock_room_success")
    await alice.close()
    await host.wait_for("participant_disconnected")

    alice2 = await live.connect_participant(alice.pid)
    await alice2.send("participant_connected", {"meeting_id": str(live.meeting_id)})

    state = await alice2.wait_for_payload("participant_state")
    assert (state["username"], state["connected"]) == ("alice", True)
    await alice2.assert_still_open()


async def test_lobby_participant_registered_before_lock_can_rejoin(live):
    host = await live.connect_host()
    ghost = await live.lobby()
    await host.send("lock_meeting")
    await ghost.wait_for("lock_room_success")
    await ghost.close()
    await host.wait_for("participant_disconnected")

    ghost2 = await live.lobby(ghost.pid)

    await ghost2.assert_still_open()


async def test_unlock_lets_new_participants_in_again(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("lock_meeting")
    await alice.wait_for("lock_room_success")
    await host.send("unlock_meeting")
    await alice.wait_for("unlock_room_success")

    newcomer = await live.lobby()

    await newcomer.assert_still_open()


# ------------------------------------------------------------------- kick
async def test_kick_closes_participant_and_reports_to_host(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    bob = await live.join("bob")
    await bob.wait_for(
        "participants_state", where=lambda m: len(m["payload"]["participants"]) == 2
    )

    await host.send("kick_participant", {"id": str(alice.pid)})

    closed = await alice.wait_closed()
    assert (closed.code, closed.reason) == (
        4002,
        "You have been kicked from the meeting.",
    )
    result = await host.wait_for_payload("kick_participant_success")
    assert result == {
        "detail": "The participant has been kicked from the meeting.",
        "kicked": True,
        "id": str(alice.pid),
    }
    # remaining participants receive the list without the kicked one
    state = await bob.wait_for_payload(
        "participants_state",
        where=lambda m: (
            [p["id"] for p in m["payload"]["participants"]] == [str(bob.pid)]
        ),
    )
    assert state["participants"][0]["username"] == "bob"


async def test_kicked_participant_is_blocked_from_reconnecting(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("kick_participant", {"id": str(alice.pid)})
    await alice.wait_closed()
    await host.wait_for("kick_participant_success")

    again = await live.connect_participant(alice.pid)

    closed = await again.wait_closed()
    assert (closed.code, closed.reason) == (4002, "participant kicked from meeting")


async def test_kicked_participant_is_blocked_even_when_room_is_locked(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("kick_participant", {"id": str(alice.pid)})
    await host.wait_for("kick_participant_success")
    await host.send("lock_meeting")

    again = await live.connect_participant(alice.pid)

    assert (await again.wait_closed()).code == 4002


async def test_kick_unknown_participant_fails(live):
    host = await live.connect_host()
    ghost = uuid.uuid4()

    await host.send("kick_participant", {"id": str(ghost)})

    result = await host.wait_for_payload("kick_participant_failed")
    assert result == {
        "detail": "Participant not found. They may have already left the meeting.",
        "kicked": False,
        "id": str(ghost),
    }


async def test_kicked_username_becomes_available_again(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("kick_participant", {"id": str(alice.pid)})
    await host.wait_for("kick_participant_success")
    bob = await live.lobby()

    await bob.send("participant_join_room", {"username": "alice"})

    await bob.wait_for("participant_join_room_success")


async def test_kick_lobby_participant(live):
    host = await live.connect_host()
    lobby_user = await live.lobby()

    await host.send("kick_participant", {"id": str(lobby_user.pid)})

    assert (await lobby_user.wait_closed()).code == 4002
    await host.wait_for("kick_participant_success")


async def test_kicked_participant_frees_a_cap_slot(live, make_meeting):
    meeting = await make_meeting(participant_cap=1)
    host = await live.connect_host(meeting_id=meeting.id)
    alice = await live.join("alice", meeting_id=meeting.id)
    await host.send("kick_participant", {"id": str(alice.pid)})
    await host.wait_for("kick_participant_success")

    bob = await live.lobby(meeting_id=meeting.id)

    await bob.assert_still_open()
