"""Timeouts (stale host / stale lobby), duration timer and SIGTERM."""

import asyncio

from sqlalchemy import select

from src.models import Meeting, User
from src.types import MeetingStatus
from tests.live.builders import question_out


async def _fresh(session, model, pk):
    result = await session.execute(
        select(model).where(model.id == pk).execution_options(populate_existing=True)
    )
    return result.scalar_one()


# stale host
async def test_stale_host_room_is_ended_after_timeout(
    live, live_manager, short_timeouts, meeting, host_user, session
):
    live_manager.STALE_LOBBY_TIMEOUT_SECONDS = 600  # isolate the host timeout
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("meeting_started", {"question": question_out(meeting.id)})
    await alice.wait_for("meeting_started")

    await host.close()

    await alice.wait_for("host_disconnected")
    await alice.wait_for("meeting_ended", timeout=short_timeouts + 2)
    db_meeting = await _fresh(session, Meeting, meeting.id)
    db_user = await _fresh(session, User, host_user.id)
    assert db_meeting.status == MeetingStatus.DRAFT
    assert db_meeting.started_at is None
    assert db_user.live_meeting is False
    newcomer = await live.connect_participant()
    assert (await newcomer.wait_closed()).code == 4001


async def test_host_reconnecting_in_time_cancels_the_stale_timeout(
    live, live_manager, meeting
):
    live_manager.STALE_HOST_TIMEOUT_SECONDS = 0.5
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("meeting_started", {"question": question_out(meeting.id)})
    await alice.wait_for("meeting_started")
    await host.close()
    await alice.wait_for("host_disconnected")

    host2 = await live.connect_host(ready=False)
    await host2.wait_for("meeting_state")
    await asyncio.sleep(0.8)  # well past the original timeout

    await alice.assert_not_received("meeting_ended")
    await alice.assert_still_open()
    late = await live.lobby()
    await late.assert_still_open()


async def test_each_host_disconnect_restarts_the_full_stale_timeout(
    live, live_manager, meeting
):
    """The timer armed by an earlier disconnect must not outlive a reconnect.

    disconnect#1 arms a 0.6s timer; the host reconnects (cancelling it) and
    disconnects again at ~0.35s, arming a fresh timer that fires at ~0.95s. If
    the first timer survived it would end the meeting at ~0.6s.
    """
    live_manager.STALE_HOST_TIMEOUT_SECONDS = 0.6
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("meeting_started", {"question": question_out(meeting.id)})
    await alice.wait_for("meeting_started")
    await host.close()
    await alice.wait_for("host_disconnected")
    host2 = await live.connect_host(ready=False)
    await host2.wait_for("meeting_state")
    await asyncio.sleep(0.25)
    await host2.close()
    await alice.wait_for("host_disconnected")

    await alice.assert_not_received("meeting_ended", within=0.4)  # past 0.6s mark

    await alice.wait_for("meeting_ended", timeout=2)


# stale lobby
async def test_room_that_never_started_is_ended_after_lobby_timeout(
    live, short_timeouts, meeting, host_user, session
):
    host = await live.connect_host()
    alice = await live.join("alice")

    await alice.wait_for("meeting_ended", timeout=short_timeouts + 2)
    await host.wait_for("meeting_ended")
    db_meeting = await _fresh(session, Meeting, meeting.id)
    db_user = await _fresh(session, User, host_user.id)
    assert db_meeting.status == MeetingStatus.DRAFT
    assert db_user.live_meeting is False
    newcomer = await live.connect_participant()
    assert (await newcomer.wait_closed()).code == 4001


async def test_starting_the_meeting_cancels_the_lobby_timeout(
    live, short_timeouts, meeting
):
    host = await live.connect_host()
    alice = await live.join("alice")
    await host.send("meeting_started", {"question": question_out(meeting.id)})
    await alice.wait_for("meeting_started")

    await asyncio.sleep(short_timeouts * 3)

    await alice.assert_not_received("meeting_ended")
    await host.assert_not_received("meeting_ended")
    late = await live.lobby()
    await late.assert_still_open()


# duration timer
async def test_meeting_ends_itself_when_its_duration_elapses(
    live, fast_meeting_timer, make_meeting, session
):
    meeting = await make_meeting(duration=1)
    host = await live.connect_host(meeting_id=meeting.id)
    alice = await live.join("alice", meeting_id=meeting.id)

    await host.send("meeting_started", {"question": question_out(meeting.id)})

    await alice.wait_for("meeting_ended", timeout=fast_meeting_timer + 2)
    await host.wait_for("meeting_ended")
    db_meeting = await _fresh(session, Meeting, meeting.id)
    assert db_meeting.status == MeetingStatus.COMPLETED
    newcomer = await live.connect_participant(meeting_id=meeting.id)
    assert (await newcomer.wait_closed()).code == 4001


# sigterm
async def test_sigterm_closes_every_socket_and_resets_the_meeting(
    live, live_manager, meeting, host_user, session
):
    host = await live.connect_host()
    alice = await live.join("alice")
    lobby_user = await live.lobby()
    await host.send("meeting_started", {"question": question_out(meeting.id)})
    await alice.wait_for("meeting_started")

    await live_manager.close_rooms()

    for client in (host, alice, lobby_user):
        closed = await client.wait_closed()
        assert (closed.code, closed.reason) == (
            1012,
            "meeting ended due to server shutdown",
        )
    db_meeting = await _fresh(session, Meeting, meeting.id)
    db_user = await _fresh(session, User, host_user.id)
    assert db_meeting.status == MeetingStatus.DRAFT
    assert db_meeting.started_at is None
    assert db_user.live_meeting is False
    newcomer = await live.connect_participant()
    assert (await newcomer.wait_closed()).code == 4001


async def test_sigterm_with_no_rooms_is_a_noop(live, live_manager):
    await live_manager.close_rooms()
