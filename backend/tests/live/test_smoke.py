"""Harness smoke test: host connects, participant joins, host is told."""

from tests.live.builders import question_out


async def test_smoke_host_and_participant_round_trip(live, meeting):
    host = await live.connect_host()
    p = await live.join("alice")
    msg = await host.wait_for_payload(
        "participant_connected", where=lambda m: m["payload"]["username"] == "alice"
    )
    assert msg["is_lobby"] is False

    await host.send("meeting_started", {"question": question_out(meeting.id)})
    started = await p.wait_for_payload("meeting_started")
    assert started["question"]["type"] == "yes_no"
