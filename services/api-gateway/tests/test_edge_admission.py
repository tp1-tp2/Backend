import io
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_http_client
from app.core import edge_admission
from app.core.config import settings
from app.main import app


def _http():
    http = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b'{"ok":true}'
    resp.headers = {"content-type": "application/json"}
    http.post.return_value = resp
    return http


@pytest.fixture
def client():
    http = _http()
    app.dependency_overrides[get_http_client] = lambda: http
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "u1", "email": "u@example.com"}
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, http
    app.dependency_overrides.clear()


def _upload(c):
    return c.post("/api/v1/transcribe", files={"file": ("a.wav", io.BytesIO(b"RIFF"), "audio/wav")})


def test_disabled_by_default_passes_through(client):
    c, http = client
    assert settings.edge_max_inflight_transcribe == 0
    assert _upload(c).status_code == 200
    http.post.assert_called_once()


def test_rejects_at_edge_without_forwarding(client):
    c, http = client
    with patch.object(settings, "edge_max_inflight_transcribe", 2), \
            patch.object(edge_admission, "try_acquire", AsyncMock(return_value=(False, None))):
        resp = _upload(c)
    assert resp.status_code == 503
    assert resp.headers["Retry-After"] == str(settings.retry_after_seconds)
    assert resp.json()["errorCode"] == "SYSTEM_003"
    http.post.assert_not_called()  # audio-processor never sees the rejected upload


def test_admitted_request_releases_its_slot(client):
    c, http = client
    release = AsyncMock()
    with patch.object(settings, "edge_max_inflight_transcribe", 2), \
            patch.object(edge_admission, "try_acquire", AsyncMock(return_value=(True, "slot-1"))), \
            patch.object(edge_admission, "release", release):
        assert _upload(c).status_code == 200
    release.assert_awaited_once_with("slot-1")
    http.post.assert_called_once()


def test_other_routes_are_not_limited(client):
    c, _ = client
    acquire = AsyncMock(return_value=(False, None))
    with patch.object(settings, "edge_max_inflight_transcribe", 1), \
            patch.object(edge_admission, "try_acquire", acquire):
        c.get("/health")
    acquire.assert_not_awaited()


async def test_fails_open_when_redis_errors():
    broken = MagicMock()
    broken.register_script.side_effect = ConnectionError("redis down")
    with patch.object(settings, "edge_max_inflight_transcribe", 1), \
            patch.object(edge_admission, "get_redis", return_value=broken), \
            patch.object(edge_admission, "_acquire_script", None):
        assert await edge_admission.try_acquire() == (True, None)


async def test_cap_is_enforced_with_a_shared_counter():
    """Exercise the real acquire/release path against an in-memory stand-in
    for the Redis script: the cap holds and released slots are reusable."""
    held: dict[str, float] = {}

    async def script(keys, args):
        now, stale, cap, slot = float(args[0]), float(args[1]), int(args[2]), args[3]
        for k in [k for k, ts in held.items() if ts <= stale]:
            held.pop(k)
        if len(held) >= cap:
            return 0
        held[slot] = now
        return 1

    fake = MagicMock()
    fake.register_script.return_value = script
    fake.zrem = AsyncMock(side_effect=lambda key, slot: held.pop(slot, None))
    with patch.object(settings, "edge_max_inflight_transcribe", 2), \
            patch.object(edge_admission, "get_redis", return_value=fake), \
            patch.object(edge_admission, "_acquire_script", None):
        a = await edge_admission.try_acquire()
        b = await edge_admission.try_acquire()
        c = await edge_admission.try_acquire()
        assert a[0] and b[0] and c == (False, None)
        await edge_admission.release(a[1])
        assert (await edge_admission.try_acquire())[0]


async def test_release_survives_cancellation_of_the_request_task():
    """A client disconnect cancels the request inside an anyio cancel scope
    (Starlette); every await in the `finally` is cancelled too unless shielded.
    The slot must still be released (it used to leak until stale, throttling
    the start of the next E4 run)."""
    import asyncio

    import anyio

    from app.main import edge_admission_middleware

    released = asyncio.Event()
    scope_box = {}

    async def slow_release(slot):
        await asyncio.sleep(0.05)
        released.set()

    async def call_next(_request):
        await asyncio.sleep(10)

    async def handle():
        with anyio.CancelScope() as scope:
            scope_box["scope"] = scope
            await edge_admission_middleware(request, call_next)

    request = MagicMock()
    request.method = "POST"
    request.url.path = "/api/v1/transcribe"
    with patch.object(settings, "edge_max_inflight_transcribe", 1),             patch.object(edge_admission, "try_acquire", AsyncMock(return_value=(True, "s1"))),             patch.object(edge_admission, "release", slow_release):
        task = asyncio.create_task(handle())
        await asyncio.sleep(0.05)
        scope_box["scope"].cancel()
        await task
        await asyncio.wait_for(released.wait(), 2)
    assert released.is_set()
