"""Handshake authentication with the real JWT dependencies (no overrides)."""

import datetime
import uuid

import jwt as pyjwt

from src.auth.token import (
    JWT_ALGORITHM,
    generate_access_token,
    generate_participants_meeting_access_token,
)
from src.config import get_settings
from src.types import MeetingStatus
from src.utils import generate_participants_meeting_access_token_key


def _host_headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Cookie": f"access_token={generate_access_token(u_id=user_id)}"}


def _participant_headers(
    meeting_id: uuid.UUID, participant_id: uuid.UUID, *, cookie_meeting_id=None
) -> dict[str, str]:
    token = generate_participants_meeting_access_token(
        duration=300, m_id=meeting_id, p_id=participant_id
    )
    key = generate_participants_meeting_access_token_key(
        m_id=str(cookie_meeting_id or meeting_id)
    )
    return {"Cookie": f"{key}={token}"}


# host
async def test_host_with_valid_token_connects(live_real_auth, host_user, meeting):
    live = live_real_auth
    host = await live.connect_host(headers=_host_headers(host_user.id))

    await host.assert_still_open()
    assert not host.rejected_before_accept


async def test_host_without_token_is_rejected_before_accept(live_real_auth):
    host = await live_real_auth.connect_host(ready=False, headers={})

    assert host.rejected_before_accept
    closed = await host.wait_closed()
    assert closed.code == 1008


async def test_host_with_garbage_token_is_rejected_before_accept(live_real_auth):
    host = await live_real_auth.connect_host(
        ready=False, headers={"Cookie": "access_token=not-a-jwt"}
    )

    assert host.rejected_before_accept
    assert (await host.wait_closed()).code == 1008


async def test_host_with_token_of_unknown_user_is_rejected(live_real_auth):
    host = await live_real_auth.connect_host(
        ready=False, headers=_host_headers(uuid.uuid4())
    )

    assert host.rejected_before_accept
    assert (await host.wait_closed()).code == 1008


async def test_host_with_expired_token_is_rejected(live_real_auth, host_user):
    settings = get_settings()
    now = datetime.datetime.now(datetime.UTC)
    token = pyjwt.encode(
        {
            "user_id": str(host_user.id),
            "exp": now - datetime.timedelta(minutes=1),
            "iat": now - datetime.timedelta(hours=1),
            "type": "access",
        },
        settings.JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    host = await live_real_auth.connect_host(
        ready=False, headers={"Cookie": f"access_token={token}"}
    )

    assert host.rejected_before_accept
    assert (await host.wait_closed()).code == 1008


# -------------------------------------------------------------- participant
async def test_participant_with_valid_token_joins(live_real_auth, host_user, meeting):
    live = live_real_auth
    await live.connect_host(headers=_host_headers(host_user.id))
    token_pid = uuid.uuid4()

    # the (ignored) query string carries a different id than the token
    p = await live.connect_participant(
        uuid.uuid4(), headers=_participant_headers(meeting.id, token_pid)
    )
    await p.send("participant_connected", {"meeting_id": str(meeting.id)})

    state = await p.wait_for_payload("participant_state")
    assert state["id"] == str(token_pid)  # identity comes from the token


async def test_participant_without_token_gets_meeting_not_found(live_real_auth):
    p = await live_real_auth.connect_participant(headers={})

    closed = await p.wait_closed()
    assert (closed.code, closed.reason) == (4001, "meeting not found")
    assert not p.rejected_before_accept  # accepted, then closed with the code


async def test_participant_with_garbage_token_gets_meeting_not_found(live_real_auth):
    live = live_real_auth
    key = generate_participants_meeting_access_token_key(m_id=str(live.meeting_id))

    p = await live.connect_participant(headers={"Cookie": f"{key}=garbage"})

    assert (await p.wait_closed()).code == 4001


async def test_participant_token_for_another_meeting_is_refused(
    live_real_auth, make_meeting, host_user
):
    live = live_real_auth
    other = await make_meeting()
    await live.connect_host(headers=_host_headers(host_user.id))
    pid = uuid.uuid4()
    # a valid token for `other`, presented as the cookie of this meeting
    headers = _participant_headers(other.id, pid, cookie_meeting_id=live.meeting_id)

    p = await live.connect_participant(pid, headers=headers)

    assert (await p.wait_closed()).code == 4001


async def test_participant_token_for_completed_meeting_is_refused(
    live_real_auth, make_meeting, session
):
    live = live_real_auth
    done = await make_meeting(status=MeetingStatus.COMPLETED)
    pid = uuid.uuid4()

    p = await live.connect_participant(
        pid, meeting_id=done.id, headers=_participant_headers(done.id, pid)
    )

    assert (await p.wait_closed()).code == 4001
