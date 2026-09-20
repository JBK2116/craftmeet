"""AI snapshot requests (the OpenAI call is stubbed)."""

import re
import uuid

GENERIC_FAILURE = {"detail": "Unable to generate snapshot at the current time."}


async def test_snapshot_success(live, meeting, ai_summary):
    host = await live.connect_host()

    await host.send("get_snapshot", {"meeting_id": str(meeting.id)})

    payload = await host.wait_for_payload("get_snapshot_success")
    snapshot = payload["snapshot"]
    assert snapshot["mood"] == "positive"
    assert snapshot["attention_flag"] == "none"
    assert snapshot["suggested_question_prompt"] == "What next?"
    assert "created_at" in snapshot
    ai_summary.assert_awaited_once()


async def test_snapshot_for_another_meeting_is_refused(live, ai_summary):
    host = await live.connect_host()

    await host.send("get_snapshot", {"meeting_id": str(uuid.uuid4())})

    assert await host.wait_for_payload("get_snapshot_failed") == GENERIC_FAILURE
    ai_summary.assert_not_awaited()


async def test_snapshot_is_rate_limited_for_three_minutes(live, meeting, ai_summary):
    host = await live.connect_host()
    await host.send("get_snapshot", {"meeting_id": str(meeting.id)})
    await host.wait_for("get_snapshot_success")

    await host.send("get_snapshot", {"meeting_id": str(meeting.id)})

    payload = await host.wait_for_payload("get_snapshot_failed")
    assert re.fullmatch(r"Try again in \d+ (minute|second)\(s\)\.", payload["detail"])
    assert ai_summary.await_count == 1


async def test_snapshot_ai_failure_is_reported(live, meeting, ai_summary):
    ai_summary.return_value = None
    host = await live.connect_host()

    await host.send("get_snapshot", {"meeting_id": str(meeting.id)})

    assert await host.wait_for_payload("get_snapshot_failed") == GENERIC_FAILURE


async def test_snapshot_unparseable_ai_output_is_reported(live, meeting, ai_summary):
    ai_summary.return_value = "definitely not json"
    host = await live.connect_host()

    await host.send("get_snapshot", {"meeting_id": str(meeting.id)})

    assert await host.wait_for_payload("get_snapshot_failed") == GENERIC_FAILURE


async def test_snapshot_invalid_ai_shape_is_reported(live, meeting, ai_summary):
    ai_summary.return_value = '{"mood": "ecstatic"}'
    host = await live.connect_host()

    await host.send("get_snapshot", {"meeting_id": str(meeting.id)})

    assert await host.wait_for_payload("get_snapshot_failed") == GENERIC_FAILURE


async def test_failed_snapshot_does_not_start_the_cooldown(live, meeting, ai_summary):
    ai_summary.return_value = None
    host = await live.connect_host()
    await host.send("get_snapshot", {"meeting_id": str(meeting.id)})
    await host.wait_for("get_snapshot_failed")
    ai_summary.return_value = (
        '{"mood":"mixed","attention_flag":"x","suggested_question_prompt":"y"}'
    )

    await host.send("get_snapshot", {"meeting_id": str(meeting.id)})

    payload = await host.wait_for_payload("get_snapshot_success")
    assert payload["snapshot"]["mood"] == "mixed"
