"""Black-box WebSocket harness for the live meeting contract tests.

Everything here talks to the app only through the WebSocket boundary
(connect, send JSON, receive JSON, observe close codes), so the same tests
gate both the current implementation and its rewrite.

Design notes
------------
* Outbound message order is not deterministic (the server fans out with
  fire-and-forget tasks), so ``WSClient.wait_for`` searches by message *type*
  and never asserts "the next message is X".
* ``httpx-ws`` sessions use anyio cancel scopes, which must be entered and
  exited from the same task. pytest-asyncio runs fixture setup, the test body
  and fixture teardown in different tasks, so every connection (and the
  transport itself) is owned by a dedicated task started here.
"""

import asyncio
import contextlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import httpx
from fastapi import FastAPI
from httpx_ws import (
    WebSocketDisconnect,
    WebSocketNetworkError,
    WebSocketUpgradeError,
    aconnect_ws,
)
from httpx_ws.transport import ASGIWebSocketTransport

DEFAULT_TIMEOUT = 2.0
NEGATIVE_WINDOW = 0.3  # how long to wait before concluding "nothing arrived"


@dataclass(frozen=True)
class Closed:
    code: int
    reason: str | None


class ErrorCapturingApp:
    """ASGI wrapper recording exceptions that escape the application.

    A handler that crashes after it already sent a close frame is invisible
    to the client, so contract tests also assert on this list.
    """

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.errors: list[BaseException] = []

    async def __call__(self, scope, receive, send) -> None:
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            self.errors.append(exc)
            raise


class WSClient:
    """One WebSocket connection with a searchable inbox and close tracking."""

    def __init__(self, http: httpx.AsyncClient, url: str, headers: dict | None):
        self.url = url
        self._http = http
        self._headers = headers or {}
        self._ws = None
        self._buffer: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = []
        self.closed: Closed | None = None
        self.rejected_before_accept = False
        self.upgrade_status: int | None = None
        self._changed = asyncio.Event()
        self._connected = asyncio.Event()
        self._done = asyncio.Event()
        self._task = asyncio.create_task(self._run())

    # ------------------------------------------------------------------ pump
    async def _run(self) -> None:
        try:
            async with aconnect_ws(
                self.url,
                self._http,
                headers=self._headers,
                keepalive_ping_interval_seconds=None,
            ) as ws:
                self._ws = ws
                self._connected.set()
                while True:
                    try:
                        data = await ws.receive_json()
                    except WebSocketDisconnect as exc:
                        self.closed = Closed(exc.code, exc.reason)
                        break
                    except WebSocketNetworkError:
                        break
                    self._buffer.append(data)
                    self.history.append(data)
                    self._changed.set()
        except WebSocketDisconnect as exc:
            # server closed before accepting the handshake
            self.closed = Closed(exc.code, exc.reason)
            self.rejected_before_accept = True
        except WebSocketUpgradeError as exc:
            self.upgrade_status = exc.response.status_code
            self.rejected_before_accept = True
        finally:
            self._connected.set()
            self._done.set()
            self._changed.set()

    async def wait_connected(self) -> "WSClient":
        await asyncio.wait_for(self._connected.wait(), DEFAULT_TIMEOUT)
        return self

    # --------------------------------------------------------------- sending
    async def send(self, type_: str, payload: Any = None) -> None:
        msg: dict[str, Any] = {"type": type_}
        if payload is not None:
            msg["payload"] = payload
        assert self._ws is not None, "socket not open"
        await self._ws.send_json(msg)

    async def send_text(self, text: str) -> None:
        assert self._ws is not None, "socket not open"
        await self._ws.send_text(text)

    async def close(self, code: int = 1000) -> None:
        """Client-initiated close; the server observes a disconnect."""
        if self._ws is not None and not self._done.is_set():
            with contextlib.suppress(Exception):
                await self._ws.close(code)
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await self._task

    # ------------------------------------------------------------- receiving
    def _find(self, type_: str, where: Callable[[dict], bool] | None) -> int | None:
        for i, msg in enumerate(self._buffer):
            if msg.get("type") == type_ and (where is None or where(msg)):
                return i
        return None

    async def wait_for(
        self,
        type_: str,
        *,
        where: Callable[[dict], bool] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        """Return (and consume) the first buffered/incoming message of a type."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            idx = self._find(type_, where)
            if idx is not None:
                return self._buffer.pop(idx)
            if self._done.is_set():
                raise AssertionError(
                    f"socket closed ({self.closed}) while waiting for {type_!r}; "
                    f"unconsumed={self._types()}"
                )
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise AssertionError(
                    f"timed out waiting for {type_!r}; unconsumed={self._types()}, "
                    f"closed={self.closed}"
                )
            self._changed.clear()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._changed.wait(), remaining)

    async def wait_for_payload(self, type_: str, **kw) -> dict[str, Any]:
        return (await self.wait_for(type_, **kw)).get("payload")

    async def assert_not_received(
        self,
        type_: str,
        *,
        where: Callable[[dict], bool] | None = None,
        within: float = NEGATIVE_WINDOW,
    ) -> None:
        """Assert no unconsumed message of ``type_`` shows up within a window."""
        await asyncio.sleep(within)
        idx = self._find(type_, where)
        assert idx is None, f"unexpected {type_!r}: {self._buffer[idx]}"

    async def wait_closed(self, timeout: float = DEFAULT_TIMEOUT) -> Closed:
        """Wait for the server to close the socket and return the close info."""
        try:
            await asyncio.wait_for(self._done.wait(), timeout)
        except TimeoutError:
            raise AssertionError(
                f"socket still open after {timeout}s; unconsumed={self._types()}"
            ) from None
        assert self.closed is not None, "socket ended without a close frame"
        return self.closed

    async def assert_still_open(self, within: float = NEGATIVE_WINDOW) -> None:
        await asyncio.sleep(within)
        assert not self._done.is_set(), f"socket unexpectedly closed: {self.closed}"

    @property
    def is_open(self) -> bool:
        return not self._done.is_set()

    def count(self, type_: str) -> int:
        """How many messages of a type were ever received (consumed or not)."""
        return sum(1 for m in self.history if m.get("type") == type_)

    def drain(self) -> list[dict[str, Any]]:
        """Consume and return everything currently buffered."""
        out, self._buffer = self._buffer, []
        return out

    def received_types(self) -> list[str]:
        return self._types()

    def _types(self) -> list[str]:
        return [m.get("type") for m in self._buffer]


async def wait_until(
    predicate: Callable[[], bool],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    message: str = "condition not reached",
) -> None:
    """Poll a condition on received state until it holds or the timeout hits."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() > deadline:
            raise AssertionError(f"timed out: {message}")
        await asyncio.sleep(0.01)


class ParticipantClient(WSClient):
    pid: uuid.UUID


class LiveHarness:
    """Owns the ASGI app, the HTTP client/transport and every open connection."""

    def __init__(self, app: FastAPI, meeting_id: uuid.UUID, host_user_id: uuid.UUID):
        self.app = ErrorCapturingApp(app)
        self.meeting_id = meeting_id
        self.host_user_id = host_user_id
        self.clients: list[WSClient] = []
        self.broken_connections: set[str] = set()
        self.hung_connections: set[str] = set()
        self.hung_sends = 0
        self._http: httpx.AsyncClient | None = None
        self._owner: asyncio.Task | None = None
        self._ready = asyncio.Event()
        self._stop = asyncio.Event()

    @property
    def server_errors(self) -> list[BaseException]:
        return self.app.errors

    # The transport holds an anyio task group, so it lives in its own task.
    async def start(self) -> None:
        async def own() -> None:
            transport = ASGIWebSocketTransport(app=self.app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as http:
                self._http = http
                self._ready.set()
                await self._stop.wait()

        self._owner = asyncio.create_task(own())
        await asyncio.wait_for(self._ready.wait(), DEFAULT_TIMEOUT)

    async def stop(self) -> None:
        for client in self.clients:
            await client.close()
        self._stop.set()
        if self._owner is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self._owner, DEFAULT_TIMEOUT)

    # ------------------------------------------------------------ connecting
    async def connect_host(
        self,
        *,
        meeting_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        headers: dict | None = None,
        ready: bool = True,
        query: str | None = None,
    ) -> WSClient:
        """Open a host socket.

        With ``ready=True`` (default) do one host round trip so the room is
        known to exist server-side before the caller continues: the server
        accepts the socket *before* it creates the room, so without a barrier a
        participant connecting right away can race the room creation.
        """
        mid = meeting_id or self.meeting_id
        conn = uuid.uuid4().hex
        qs = f"?uid={user_id or self.host_user_id}&conn={conn}"
        if query:
            qs += f"&{query}"
        client = self._open(f"/meetings/{mid}/host/ws{qs}", headers)
        client.conn = conn  # ty: ignore[unresolved-attribute]
        await client.wait_connected()
        if ready and not client.rejected_before_accept:
            await self.host_barrier(client)
        return client

    async def host_barrier(self, host: WSClient) -> None:
        """Round-trip a harmless host message through the host receive loop."""
        await host.send("kick_participant", {"id": str(uuid.uuid4())})
        await host.wait_for("kick_participant_failed")

    async def connect_participant(
        self,
        pid: uuid.UUID | None = None,
        *,
        meeting_id: uuid.UUID | None = None,
        headers: dict | None = None,
    ) -> ParticipantClient:
        """Open a participant socket (no ``participant_connected`` message yet)."""
        mid = meeting_id or self.meeting_id
        pid = pid or uuid.uuid4()
        conn = uuid.uuid4().hex
        client = self._open(
            f"/meetings/{mid}/participant/ws?pid={pid}&conn={conn}",
            headers,
            cls=ParticipantClient,
        )
        client.pid = pid
        client.conn = conn  # ty: ignore[unresolved-attribute]
        await client.wait_connected()
        return client  # ty: ignore[invalid-return-type]

    async def lobby(
        self, pid: uuid.UUID | None = None, *, meeting_id: uuid.UUID | None = None
    ) -> ParticipantClient:
        """Connect and announce with ``participant_connected`` (lobby state)."""
        mid = meeting_id or self.meeting_id
        p = await self.connect_participant(pid, meeting_id=mid)
        await p.send("participant_connected", {"meeting_id": str(mid)})
        await p.wait_for("participant_state")
        return p

    async def join(
        self,
        username: str,
        pid: uuid.UUID | None = None,
        *,
        meeting_id: uuid.UUID | None = None,
    ) -> ParticipantClient:
        """Full join: connect, lobby, then ``participant_join_room``."""
        p = await self.lobby(pid, meeting_id=meeting_id)
        await p.send("participant_join_room", {"username": username})
        await p.wait_for("participant_join_room_success")
        return p

    def _open(self, path: str, headers: dict | None, cls=WSClient) -> WSClient:
        assert self._http is not None
        client = cls(self._http, path, headers)
        self.clients.append(client)
        return client

    # ------------------------------------------------------------ fault injection
    def break_connection(self, client: WSClient) -> None:
        """Make server-side sends to this connection fail as on a dead socket."""
        self.broken_connections.add(client.conn)  # ty: ignore[unresolved-attribute]

    def hang_connection(self, client: WSClient) -> None:
        """Make server-side sends to this connection block forever (slow client)."""
        self.hung_connections.add(client.conn)  # ty: ignore[unresolved-attribute]


def fake_user(user_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(id=user_id, email=f"{user_id}@example.test", username="host")
