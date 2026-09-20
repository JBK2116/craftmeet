"""Chat fan-out, replay and per-sender token-bucket rate limiting."""

from tests.live.builders import chat
from tests.live.harness import wait_until

RATE_LIMIT_MESSAGE = "You have been rate limited. Try again soon."
# bucket capacity is 60 tokens (refill 20/s); a burst well past it must trip
BURST = 70


async def test_participant_chat_reaches_host_and_all_participants_including_sender(
    live,
):
    host = await live.connect_host()
    alice = await live.join("alice")
    bob = await live.join("bob")
    lobby_user = await live.lobby()

    await alice.send(
        "chat_received", chat(u_id=alice.pid, name="alice", message="hi all")
    )

    for client in (host, alice, bob, lobby_user):
        payload = await client.wait_for_payload("chat_received")
        assert payload["chat"]["message"] == "hi all"
        assert payload["chat"]["u_id"] == str(alice.pid)
        assert payload["chat"]["name"] == "alice"
        assert payload["chat"]["is_host"] is False
        assert "created_at" in payload["chat"]


async def test_host_chat_reaches_host_and_all_participants(live, host_user):
    host = await live.connect_host()
    alice = await live.join("alice")

    await host.send(
        "chat_received",
        chat(u_id=host_user.id, name="host", message="welcome", is_host=True),
    )

    for client in (host, alice):
        payload = await client.wait_for_payload("chat_received")
        assert payload["chat"]["message"] == "welcome"
        assert payload["chat"]["is_host"] is True
        assert payload["chat"]["u_id"] == str(host_user.id)


async def test_chat_from_lobby_participant_is_dropped(live):
    host = await live.connect_host()
    lobby_user = await live.lobby()

    await lobby_user.send("chat_received", chat(u_id=lobby_user.pid, name="lobby"))

    await host.assert_not_received("chat_received")
    await lobby_user.assert_not_received("chat_received")
    await lobby_user.assert_not_received("rate_limited")


async def test_chat_from_unregistered_participant_is_dropped(live):
    host = await live.connect_host()
    stranger = await live.connect_participant()

    await stranger.send("chat_received", chat(u_id=stranger.pid, name="stranger"))

    await host.assert_not_received("chat_received")


async def test_chat_is_replayed_in_order_to_reconnecting_host(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    for text in ("one", "two", "three"):
        await alice.send(
            "chat_received", chat(u_id=alice.pid, name="alice", message=text)
        )
        await host.wait_for(
            "chat_received",
            where=lambda m, t=text: m["payload"]["chat"]["message"] == t,
        )
    await host.close()

    host2 = await live.connect_host(ready=False)

    payload = await host2.wait_for_payload("chat_state")
    assert [c["message"] for c in payload["chats"]] == ["one", "two", "three"]


async def test_rate_limited_message_is_not_stored_or_broadcast(live):
    host = await live.connect_host()
    alice = await live.join("alice")

    for i in range(BURST):
        await alice.send(
            "chat_received", chat(u_id=alice.pid, name="alice", message=f"m{i}")
        )
    await alice.wait_for("rate_limited")
    await host.close()
    host2 = await live.connect_host(ready=False)

    stored = (await host2.wait_for_payload("chat_state"))["chats"]
    assert 60 <= len(stored) < BURST


async def test_participant_chat_rate_limit_sends_explicit_message_to_sender_only(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    bob = await live.join("bob")

    for i in range(BURST):
        await alice.send(
            "chat_received", chat(u_id=alice.pid, name="alice", message=f"m{i}")
        )

    payload = await alice.wait_for_payload("rate_limited")
    assert payload == {"message": RATE_LIMIT_MESSAGE}
    # no silent drops: every message was either delivered or answered explicitly
    await wait_until(
        lambda: host.count("chat_received") + alice.count("rate_limited") == BURST,
        message="every burst message delivered or explicitly rate limited",
    )
    assert host.count("chat_received") >= 60
    await host.assert_not_received("rate_limited")
    await bob.assert_not_received("rate_limited")


async def test_rate_limits_are_per_sender(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    bob = await live.join("bob")
    for i in range(BURST):
        await alice.send(
            "chat_received", chat(u_id=alice.pid, name="alice", message=f"m{i}")
        )
    await alice.wait_for("rate_limited")

    await bob.send("chat_received", chat(u_id=bob.pid, name="bob", message="still ok"))

    await host.wait_for(
        "chat_received", where=lambda m: m["payload"]["chat"]["message"] == "still ok"
    )
    await bob.assert_not_received("rate_limited")


async def test_host_chat_rate_limit_sends_explicit_message_to_host_only(
    live, host_user
):
    host = await live.connect_host()
    alice = await live.join("alice")

    for i in range(BURST):
        await host.send(
            "chat_received",
            chat(u_id=host_user.id, name="host", message=f"h{i}", is_host=True),
        )

    payload = await host.wait_for_payload("rate_limited")
    assert payload == {"message": RATE_LIMIT_MESSAGE}
    await alice.assert_not_received("rate_limited")
