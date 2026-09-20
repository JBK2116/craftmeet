"""Lobby -> join: username rules and broadcast side effects."""

import pytest


async def test_join_room_success_payload_and_broadcasts(live):
    host = await live.connect_host()
    lobby_mate = await live.lobby()
    alice = await live.lobby()
    await host.wait_for("participant_connected")
    await host.wait_for("participant_connected")

    await alice.send("participant_join_room", {"username": "alice"})

    success = await alice.wait_for_payload("participant_join_room_success")
    assert success["participant"] == {
        "id": str(alice.pid),
        "username": "alice",
        "connected": True,
        "has_answered": False,
        "is_lobby": False,
    }
    announced = await host.wait_for_payload(
        "participant_connected", where=lambda m: m["payload"]["username"] == "alice"
    )
    assert announced["is_lobby"] is False
    # everyone (including participants still in the lobby) gets the full list
    for client in (alice, lobby_mate):
        state = await client.wait_for_payload(
            "participants_state",
            where=lambda m: any(
                p["username"] == "alice" for p in m["payload"]["participants"]
            ),
        )
        assert {p["id"] for p in state["participants"]} == {
            str(alice.pid),
            str(lobby_mate.pid),
        }


@pytest.mark.parametrize("second_name", ["alice", "ALICE", "AlIcE"])
async def test_username_must_be_unique_case_insensitively(live, second_name):
    await live.connect_host()
    await live.join("alice")
    bob = await live.lobby()

    await bob.send("participant_join_room", {"username": second_name})

    failed = await bob.wait_for_payload("participant_join_room_failed")
    assert failed == {"detail": "A participant already exists with that username"}
    await bob.assert_not_received("participant_join_room_success")


async def test_participant_can_rejoin_with_their_own_username(live):
    await live.connect_host()
    alice = await live.join("alice")

    await alice.send("participant_join_room", {"username": "ALICE"})

    await alice.wait_for("participant_join_room_success")


async def test_join_room_before_registering_fails(live):
    await live.connect_host()
    p = await live.connect_participant()

    await p.send("participant_join_room", {"username": "alice"})

    failed = await p.wait_for_payload("participant_join_room_failed")
    assert failed == {
        "detail": "Unable to join meeting, please restart the join meeting process"
    }


async def test_username_is_free_again_after_failed_attempt_is_retried(live):
    await live.connect_host()
    await live.join("alice")
    bob = await live.lobby()
    await bob.send("participant_join_room", {"username": "alice"})
    await bob.wait_for("participant_join_room_failed")

    await bob.send("participant_join_room", {"username": "bobby"})

    await bob.wait_for("participant_join_room_success")


@pytest.mark.expects_server_error
async def test_too_short_username_is_not_handled_gracefully(live):
    """Characterization: payload validation errors escape the receive loop."""
    await live.connect_host()
    p = await live.lobby()

    await p.send("participant_join_room", {"username": "ab"})

    assert (await p.wait_closed()).code == 1011
