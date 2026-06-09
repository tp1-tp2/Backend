import asyncio
import base64
import json
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.exceptions import CapacityReachedError
from app.schemas.transcription import ErrorMessage
from app.services.streaming_service import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streaming"])


async def _validate_jwt(token: str) -> dict | None:
    """Call Auth Service to validate the token. Returns {user_id, email} or None."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.auth_service_url}/internal/auth/validate-token",
                json={"token": token},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("valid"):
                    return {"user_id": data["user_id"], "email": data["email"]}
    except Exception as exc:
        logger.warning("JWT validation failed: %s", exc)
    return None


def _error(code: str, message: str) -> str:
    return ErrorMessage(
        type="error",
        error_code=code,
        message=message,
        timestamp=datetime.now(timezone.utc),
    ).model_dump_json()


@router.websocket("/ws/stream")
async def stream(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()

    # 1. Validate JWT
    user_info = await _validate_jwt(token)
    if not user_info:
        await websocket.send_text(_error("AUTH_001", "Invalid or expired token"))
        await websocket.close(code=1008)
        return

    user_id = user_info["user_id"]

    # 2. Check capacity + create session
    try:
        session_id = await manager.connect(user_id)
    except CapacityReachedError:
        await websocket.send_text(_error("ASR_003", "Service capacity limit reached"))
        await websocket.close(code=1013)
        return

    partial_task: asyncio.Task | None = None

    async def _send_partials():
        while True:
            await asyncio.sleep(settings.streaming_partial_interval_seconds)
            partial = await manager.get_partial(session_id)
            if partial:
                try:
                    await websocket.send_text(partial.model_dump_json())
                except Exception:
                    break

    try:
        partial_task = asyncio.create_task(_send_partials())

        # 3. Main receive loop
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(_error("WS_001", "Invalid JSON"))
                continue

            if msg.get("type") == "audio":
                data_b64 = msg.get("data", "")
                try:
                    chunk_bytes = base64.b64decode(data_b64)
                    manager.append_chunk(session_id, chunk_bytes)
                except Exception:
                    await websocket.send_text(_error("WS_002", "Invalid base64 audio data"))

    except WebSocketDisconnect:
        logger.info("Client disconnected session=%s", session_id)
    finally:
        if partial_task:
            partial_task.cancel()

        # 4. Finalize: run full transcription on accumulated buffer
        final = await manager.finalize(session_id, user_id)
        if final:
            try:
                await websocket.send_text(final.model_dump_json())
            except Exception:
                pass

        await manager.disconnect(session_id)
