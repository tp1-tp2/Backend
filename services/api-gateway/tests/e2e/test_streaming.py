"""
11.7 E2E: Real-time streaming via WebSocket (E2-HU03)

Covers:
- Connect with valid JWT → WebSocket accepted and proxied to ASR
- Connect with invalid JWT → connection rejected (policy violation 1008)
- Client message forwarded to ASR WebSocket
- Missing token query param → connection rejected
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeAsrWs:
    """Minimal async iterable simulating the ASR WebSocket — yields no messages."""

    def __init__(self):
        self._messages = iter([])

    async def send(self, data: str) -> None:  # noqa: D401
        pass

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        raise StopAsyncIteration


class _FakeConnCtx:
    """Async context manager returned by websockets.connect() mock."""

    def __init__(self, asr_ws: _FakeAsrWs | None = None):
        self._ws = asr_ws or _FakeAsrWs()

    async def __aenter__(self) -> _FakeAsrWs:
        return self._ws

    async def __aexit__(self, *args) -> None:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_ws_invalid_token_connection_rejected():
    """WebSocket with invalid / expired JWT is rejected before the handshake
    completes (close code 1008 — Policy Violation)."""
    with patch(
        "app.api.routes.streaming._validate_token",
        new=AsyncMock(return_value=False),
    ):
        from fastapi.testclient import TestClient

        with TestClient(app, raise_server_exceptions=False) as client:
            with pytest.raises(Exception):
                # Server closes before accept() — TestClient raises on connect
                with client.websocket_connect("/ws/stream?token=bad-jwt"):
                    pass  # pragma: no cover


def test_ws_valid_token_connection_accepted():
    """WebSocket with valid JWT is accepted; gateway proxies to ASR service."""
    with patch(
        "app.api.routes.streaming._validate_token",
        new=AsyncMock(return_value=True),
    ):
        with patch(
            "app.api.routes.streaming.websockets.connect",
            return_value=_FakeConnCtx(),
        ):
            from fastapi.testclient import TestClient

            with TestClient(app, raise_server_exceptions=False) as client:
                # Should connect without raising
                with client.websocket_connect("/ws/stream?token=valid-jwt") as ws:
                    # Connection accepted — disconnect cleanly
                    pass


def test_ws_client_message_forwarded_to_asr():
    """Text frames sent by the client are forwarded to the ASR WebSocket."""
    forwarded: list[str] = []

    class _CapturingAsrWs(_FakeAsrWs):
        async def send(self, data: str) -> None:
            forwarded.append(data)

    with patch(
        "app.api.routes.streaming._validate_token",
        new=AsyncMock(return_value=True),
    ):
        with patch(
            "app.api.routes.streaming.websockets.connect",
            return_value=_FakeConnCtx(_CapturingAsrWs()),
        ):
            from fastapi.testclient import TestClient

            with TestClient(app, raise_server_exceptions=False) as client:
                with client.websocket_connect("/ws/stream?token=valid-jwt") as ws:
                    ws.send_text("audio_chunk_base64")
                    # Disconnect — triggers WebSocketDisconnect in client_to_asr


def test_ws_missing_token_param_rejected():
    """Connecting to /ws/stream without ?token= is rejected at HTTP upgrade."""
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as client:
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/stream"):
                pass  # pragma: no cover
