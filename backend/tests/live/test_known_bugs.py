"""Tests for the CORRECT behaviour of known bugs in the current implementation.

Each is ``xfail(strict=True)``: it fails today, and it must be un-marked
(the strict xfail turns into a failure once the bug is fixed) in the rewrite.
Tests marked ``expects_server_error`` additionally tolerate the crash that
makes them fail; drop that marker together with the xfail.
"""

import asyncio
import gc
import logging
import uuid
import weakref

import pytest

from tests.live.builders import chat, question_out, yes_no_response
from tests.live.harness import wait_until


# 1. locked-room rejection
@pytest.mark.xfail(
    strict=True,
    reason=(
        "handle_participant_initial_connect closes the socket for a locked room "
        "but does not return False; it falls through to a second accept() and "
        "returns True, so the handler raises after the close frame"
    ),
)
@pytest.mark.expects_server_error
async def test_new_participant_is_rejected_from_a_locked_room_cleanly(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("lock_meeting")
    await alice.wait_for("lock_room_success")

    newcomer = await live.connect_participant()

    closed = await newcomer.wait_closed()
    assert (closed.code, closed.reason) == (4005, "meeting is locked")
    await asyncio.sleep(0.2)
    assert live.server_errors == []  # rejected without a second accept()
    # and the rejected connection was never registered as a participant
    await host.assert_not_received("participant_connected")


# 2. chat identity spoofing
@pytest.mark.xfail(
    strict=True,
    reason="chat_received trusts the client-sent chat.is_host",
)
async def test_participant_cannot_impersonate_the_host_in_chat(live):
    host = await live.connect_host()
    alice = await live.join("alice")

    await alice.send(
        "chat_received",
        chat(u_id=alice.pid, name="alice", message="I am the host", is_host=True),
    )

    payload = await host.wait_for_payload("chat_received")
    assert payload["chat"]["is_host"] is False
    assert payload["chat"]["u_id"] == str(alice.pid)


@pytest.mark.xfail(
    strict=True,
    reason="chat_received trusts the client-sent chat.u_id",
)
async def test_participant_cannot_speak_as_another_participant(live):
    host = await live.connect_host()
    alice = await live.join("alice")
    bob = await live.join("bob")

    await alice.send(
        "chat_received", chat(u_id=bob.pid, name="bob", message="bob says hi")
    )

    payload = await host.wait_for_payload("chat_received")
    assert payload["chat"]["u_id"] == str(alice.pid)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "chat_received rate limits by the client-sent identity, so spoofing "
        "u_id/is_host lets a participant bypass their own limiter"
    ),
)
async def test_spoofing_identity_does_not_bypass_the_chat_rate_limit(live, host_user):
    host = await live.connect_host()
    alice = await live.join("alice")
    victims = [await live.join(f"victim{i}") for i in range(3)]
    identities = [(v.pid, False) for v in victims] + [(host_user.id, True)]

    burst = 150  # far past one bucket (60) but within four buckets
    for i in range(burst):
        u_id, is_host = identities[i % len(identities)]
        await alice.send(
            "chat_received",
            chat(u_id=u_id, name="alice", message=f"spam{i}", is_host=is_host),
        )

    await alice.wait_for("rate_limited")
    await wait_until(
        lambda: host.count("chat_received") + alice.count("rate_limited") == burst,
        message="every spam message delivered or explicitly rate limited",
    )
    assert host.count("chat_received") <= 62  # one bucket + a little refill


@pytest.mark.xfail(
    strict=True,
    reason=(
        "chat_received only treats a message as host chat when the client sets "
        "is_host=True; a host message with is_host=False is dropped as an "
        "unknown participant"
    ),
)
async def test_host_chat_is_stamped_as_host_regardless_of_client_fields(
    live, host_user
):
    host = await live.connect_host()
    alice = await live.join("alice")

    await host.send(
        "chat_received",
        chat(u_id=uuid.uuid4(), name="host", message="official", is_host=False),
    )

    payload = await alice.wait_for_payload("chat_received")
    assert payload["chat"]["is_host"] is True
    assert payload["chat"]["u_id"] == str(host_user.id)


# 3. response identity spoofing
@pytest.mark.xfail(
    strict=True,
    reason="response_received trusts the client-sent response.participant_id",
)
async def test_participant_cannot_answer_for_someone_else(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    bob = await live.join("bob")
    question = question_out(meeting.id)
    await host.send("meeting_started", {"question": question})
    await bob.wait_for("meeting_started")

    # alice submits a response claiming to be bob
    await alice.send("response_received", yes_no_response(question, bob.pid))

    payload = await host.wait_for_payload("response_received")
    assert payload["response"]["participant_id"] == str(alice.pid)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "a forged response marks the victim as having answered, so their own "
        "real answer is later ignored"
    ),
)
async def test_forged_response_does_not_block_the_victims_real_answer(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    bob = await live.join("bob")
    question = question_out(meeting.id)
    await host.send("meeting_started", {"question": question})
    await bob.wait_for("meeting_started")
    await alice.send("response_received", yes_no_response(question, bob.pid, False))
    await host.wait_for("response_received")

    await bob.send("response_received", yes_no_response(question, bob.pid, True))

    payload = await host.wait_for_payload(
        "response_received", where=lambda m: m["payload"]["response"]["value"] is True
    )
    assert payload["response"]["participant_id"] == str(bob.pid)


# 4. background tasks are not retained
@pytest.mark.xfail(
    strict=True,
    reason=(
        "fan-out uses bare asyncio.create_task(...) and drops the result, so a "
        "task blocked on a slow client can be garbage-collected mid-flight"
    ),
)
async def test_in_flight_sends_are_not_garbage_collected(live, meeting):
    host = await live.connect_host()
    slow = await live.join("slow")
    healthy = await live.join("healthy")
    live.hang_connection(slow)  # its socket never finishes a send

    loop = asyncio.get_running_loop()
    created: list[tuple[int, weakref.ref]] = []
    finished: set[int] = set()
    previous_factory = loop.get_task_factory()

    def recording_factory(loop_, coro, **kwargs):
        task = asyncio.Task(coro, loop=loop_, **kwargs)
        n = len(created)
        created.append((n, weakref.ref(task)))
        task.add_done_callback(lambda _t, n=n: finished.add(n))
        return task

    loop.set_task_factory(recording_factory)
    try:
        await host.send("meeting_started", {"question": question_out(meeting.id)})
        await healthy.wait_for("meeting_started")  # the fan-out ran
        await wait_until(lambda: live.hung_sends >= 1, message="a send hung")
        for _ in range(3):
            gc.collect()
            await asyncio.sleep(0.05)
        lost = [n for n, ref in created if ref() is None and n not in finished]
    finally:
        loop.set_task_factory(previous_factory)

    assert lost == [], f"{len(lost)} in-flight task(s) were garbage-collected"


# 5. room-destroyed log context
@pytest.mark.xfail(
    strict=True,
    reason=(
        "__destroy_room passes the context dict as a positional format arg "
        "instead of extra=, so the record has no room_id attribute"
    ),
)
async def test_room_destroyed_log_carries_room_id_as_context(live, meeting, caplog):
    caplog.set_level(logging.DEBUG)
    host = await live.connect_host()
    await host.send("meeting_started", {"question": question_out(meeting.id)})

    await host.send("meeting_ended")
    await host.wait_for("meeting_ended")

    records = [r for r in caplog.records if "room destroyed" in r.getMessage()]
    assert records, "no 'room destroyed' log record emitted"
    assert {getattr(r, "room_id", None) for r in records} == {str(meeting.id)}


# additional bugs found while characterizing
@pytest.mark.xfail(
    strict=True,
    reason=(
        "handle_participant_disconnect looks the participant up by id only, so "
        "the old socket disconnecting after a reconnect marks the participant "
        "disconnected and drops their NEW socket from every broadcast"
    ),
)
async def test_old_socket_closing_after_reconnect_keeps_new_socket_registered(
    live, meeting
):
    host = await live.connect_host()
    alice = await live.join("alice")
    alice2 = await live.connect_participant(alice.pid)
    await alice2.send("participant_connected", {"meeting_id": str(live.meeting_id)})
    await alice.wait_closed()  # the old socket is evicted
    await alice2.wait_for("participant_state")
    await asyncio.sleep(0.2)  # let the old handler run its disconnect path

    await host.send("meeting_started", {"question": question_out(meeting.id)})

    await alice2.wait_for("meeting_started")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "handle_host_disconnect clears room.host without checking which socket "
        "disconnected, so a taken-over host's old socket closing later marks "
        "the NEW host as disconnected"
    ),
)
async def test_old_host_closing_after_takeover_does_not_disconnect_new_host(live):
    host = await live.connect_host()
    p = await live.join("alice")
    live.break_connection(host)
    host2 = await live.connect_host(ready=False)
    await host2.wait_for("meeting_state")
    await p.wait_for("host_reconnected")

    await host.close()  # the stale socket finally goes away

    await p.assert_not_received("host_disconnected")
