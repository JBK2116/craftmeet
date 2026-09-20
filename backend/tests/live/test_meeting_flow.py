"""Start / next question / add question / reveal / responses / end."""

import uuid

from sqlalchemy import func, select

from src.models import Meeting, Question, Stat, User, YesNoResponse
from src.types import MeetingStatus
from tests.live.builders import (
    new_question_in,
    question_out,
    rating_response,
    yes_no_response,
)


async def _fresh(session, model, pk):
    result = await session.execute(
        select(model).where(model.id == pk).execution_options(populate_existing=True)
    )
    return result.scalar_one()


# start
async def test_start_meeting_broadcasts_question_and_persists_start(
    live, meeting, session
):
    host = await live.connect_host()
    alice = await live.join("alice")
    lobby_mate = await live.lobby()
    question = question_out(meeting.id)

    await host.send("meeting_started", {"question": question})

    for client in (alice, lobby_mate):
        payload = await client.wait_for_payload("meeting_started")
        assert payload["question"]["id"] == question["id"]
        assert (
            payload["question"]["sub_question"]["id"]
            == (question["sub_question"]["id"])
        )
    db_meeting = await _fresh(session, Meeting, meeting.id)
    assert db_meeting.started_at is not None


# next question
async def test_next_question_broadcasts_and_resets_answered_flags(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    q1, q2 = question_out(meeting.id), question_out(meeting.id, position=2)
    await host.send("meeting_started", {"question": q1})
    await alice.wait_for("meeting_started")
    await alice.send("response_received", yes_no_response(q1, alice.pid))
    await host.wait_for("response_received")

    await host.send("next_question", {"question": q2})

    payload = await alice.wait_for_payload("next_question")
    assert payload["question"]["id"] == q2["id"]
    await host.close()
    host2 = await live.connect_host(ready=False)
    state = await host2.wait_for_payload("meeting_state")
    assert state["question"]["id"] == q2["id"]
    assert [p["has_answered"] for p in state["participants"]] == [False]
    assert state["responses"] == []  # responses are tracked per question


async def test_participant_can_answer_again_after_next_question(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    q1, q2 = question_out(meeting.id), question_out(meeting.id, position=2)
    await host.send("meeting_started", {"question": q1})
    await alice.send("response_received", yes_no_response(q1, alice.pid))
    await host.wait_for("response_received")
    await host.send("next_question", {"question": q2})
    await alice.wait_for("next_question")

    await alice.send("response_received", yes_no_response(q2, alice.pid, False))

    payload = await host.wait_for_payload("response_received")
    assert payload["response"]["question_id"] == q2["sub_question"]["id"]
    assert payload["response"]["value"] is False


# add question
async def test_add_question_success_persists_and_replies_to_host(
    live, meeting, session
):
    host = await live.connect_host()

    await host.send("add_question", new_question_in())

    payload = await host.wait_for_payload("add_question_success")
    q = payload["question"]
    assert (q["type"], q["prompt"], q["position"], q["meeting_id"]) == (
        "yes_no",
        "Added mid-meeting?",
        2,
        str(meeting.id),
    )
    stored = (
        await session.execute(select(Question).where(Question.id == uuid.UUID(q["id"])))
    ).scalar_one()
    assert stored.meeting_id == meeting.id


async def test_add_question_failure_is_reported_to_host(live, failing_question_insert):
    host = await live.connect_host()

    await host.send("add_question", new_question_in())

    payload = await host.wait_for_payload("add_question_failed")
    assert payload == {"detail": "Failed to add question"}


# reveal
async def test_reveal_broadcasts_current_responses(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    bob = await live.join("bob")
    question = question_out(meeting.id)
    await host.send("meeting_started", {"question": question})
    await alice.send("response_received", yes_no_response(question, alice.pid))
    await host.wait_for("response_received")

    await host.send("reveal")

    for client in (alice, bob):
        payload = await client.wait_for_payload("reveal")
        assert [r["participant_id"] for r in payload["responses"]] == [str(alice.pid)]


async def test_reveal_is_replayed_to_late_joiners(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    question = question_out(meeting.id)
    await host.send("meeting_started", {"question": question})
    await alice.send("response_received", yes_no_response(question, alice.pid))
    await host.wait_for("response_received")
    await host.send("reveal")
    await alice.wait_for("reveal")

    late = await live.lobby()

    payload = await late.wait_for_payload("reveal")
    assert [r["participant_id"] for r in payload["responses"]] == [str(alice.pid)]
    await late.wait_for("current_question")


async def test_reveal_is_replayed_to_reconnecting_participant(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("meeting_started", {"question": question_out(meeting.id)})
    await host.send("reveal")
    await alice.wait_for("reveal")
    await alice.close()
    await host.wait_for("participant_disconnected")

    alice2 = await live.lobby(alice.pid)

    await alice2.wait_for("reveal")


async def test_reveal_is_not_replayed_after_next_question(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("meeting_started", {"question": question_out(meeting.id)})
    await host.send("reveal")
    await alice.wait_for("reveal")
    await host.send("next_question", {"question": question_out(meeting.id, position=2)})
    await alice.wait_for("next_question")

    late = await live.lobby()

    await late.wait_for("current_question")
    await late.assert_not_received("reveal")


async def test_no_reveal_replay_when_nothing_was_revealed(live, meeting):
    host = await live.connect_host()
    await host.send("meeting_started", {"question": question_out(meeting.id)})
    await live.host_barrier(host)

    late = await live.lobby()

    await late.wait_for("current_question")
    await late.assert_not_received("reveal")


# responses
async def test_response_is_forwarded_to_host_only(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    bob = await live.join("bob")
    question = question_out(meeting.id)
    await host.send("meeting_started", {"question": question})
    await bob.wait_for("meeting_started")

    await alice.send("response_received", yes_no_response(question, alice.pid, True))

    payload = await host.wait_for_payload("response_received")
    assert payload == {
        "response": {
            "type": "yes_no",
            "question_id": question["sub_question"]["id"],
            "participant_id": str(alice.pid),
            "value": True,
        }
    }
    await bob.assert_not_received("response_received")
    await alice.assert_not_received("response_received")


async def test_only_one_response_per_participant_per_question(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    question = question_out(meeting.id)
    await host.send("meeting_started", {"question": question})
    await alice.send("response_received", yes_no_response(question, alice.pid, True))
    await host.wait_for("response_received")

    await alice.send("response_received", yes_no_response(question, alice.pid, False))

    await host.assert_not_received("response_received")
    await host.send("reveal")
    payload = await alice.wait_for_payload("reveal")
    assert [r["value"] for r in payload["responses"]] == [True]


async def test_lobby_participant_cannot_respond(live, meeting):
    host = await live.connect_host()
    lobby_user = await live.lobby()
    question = question_out(meeting.id)
    await host.send("meeting_started", {"question": question})
    await lobby_user.wait_for("meeting_started")

    await lobby_user.send(
        "response_received", yes_no_response(question, lobby_user.pid)
    )

    await host.assert_not_received("response_received")


async def test_response_from_unregistered_participant_is_ignored(live, meeting):
    host = await live.connect_host()
    question = question_out(meeting.id)
    await host.send("meeting_started", {"question": question})
    stranger = await live.connect_participant()

    await stranger.send("response_received", yes_no_response(question, stranger.pid))

    await host.assert_not_received("response_received")


async def test_responses_of_each_question_type_round_trip(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    question = question_out(meeting.id, type_="rating_scale")
    await host.send("meeting_started", {"question": question})
    await alice.wait_for("meeting_started")

    await alice.send("response_received", rating_response(question, alice.pid, 4))

    payload = await host.wait_for_payload("response_received")
    assert (payload["response"]["type"], payload["response"]["value"]) == (
        "rating_scale",
        4,
    )


# end
async def test_end_meeting_notifies_everyone_persists_and_destroys_room(
    live, meeting, host_user, session
):
    host = await live.connect_host()
    alice = await live.join("alice")
    bob = await live.join("bob")
    question = question_out(meeting.id)
    await host.send("meeting_started", {"question": question})
    await alice.send("response_received", yes_no_response(question, alice.pid))
    await host.wait_for("response_received")

    await host.send("meeting_ended")

    for client in (host, alice, bob):
        await client.wait_for("meeting_ended")
    db_meeting = await _fresh(session, Meeting, meeting.id)
    db_user = await _fresh(session, User, host_user.id)
    assert db_meeting.status == MeetingStatus.COMPLETED
    assert db_meeting.ended_at is not None
    assert db_user.live_meeting is False
    assert (db_user.total_meetings, db_user.total_participants) == (1, 2)
    stat = (
        await session.execute(
            select(Stat)
            .where(Stat.meeting_id == meeting.id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert (
        stat.total_participants,
        stat.total_questions_asked,
        stat.total_responses_received,
    ) == (2, 1, 1)
    persisted = await session.scalar(select(func.count()).select_from(YesNoResponse))
    assert persisted == 1
    # the room is gone
    newcomer = await live.connect_participant()
    assert (await newcomer.wait_closed()).code == 4001


async def test_host_gets_a_fresh_room_after_the_meeting_ended(live, meeting):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("meeting_started", {"question": question_out(meeting.id)})
    await host.send("meeting_ended")
    await host.wait_for("meeting_ended")
    await alice.wait_for("meeting_ended")
    await host.close()

    host2 = await live.connect_host()  # new room: no state replay
    bob = await live.lobby()

    await host2.assert_not_received("meeting_state")
    state = await bob.wait_for_payload("participants_state")
    assert [p["id"] for p in state["participants"]] == [str(bob.pid)]
    await bob.assert_not_received("current_question")
