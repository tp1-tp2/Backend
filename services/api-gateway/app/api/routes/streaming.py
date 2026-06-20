import asyncio
import logging

import httpx
import websockets
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import settings

router = APIRouter(tags=["streaming"])
logger = logging.getLogger(__name__)


async def _validate_token(token: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.auth_service_url}/internal/auth/validate-token",
                json={"token": token},
            )
            return resp.status_code == 200 and resp.json().get("valid", False)
    except Exception:
        return False


@router.websocket("/ws/stream")
async def ws_proxy(websocket: WebSocket, token: str = Query(...), sample_rate: int = Query(16000)):
    if not await _validate_token(token):
        await websocket.close(code=1008)
        return

    await websocket.accept()

    asr_ws_url = (
        settings.asr_service_url.replace("http://", "ws://").replace("https://", "wss://")
        + f"/ws/stream?token={token}&sample_rate={sample_rate}"
    )

    try:
        async with websockets.connect(asr_ws_url) as asr_ws:

            async def client_to_asr():
                try:
                    while True:
                        message = await websocket.receive()
                        if message["type"] == "websocket.disconnect":
                            break
                        # Forward binary (MediaRecorder chunks) or text as-is
                        if message.get("bytes"):
                            await asr_ws.send(message["bytes"])
                        elif message.get("text"):
                            await asr_ws.send(message["text"])
                except WebSocketDisconnect:
                    pass
                finally:
                    # Signal asr-service that the client is done
                    try:
                        await asr_ws.close()
                    except Exception:
                        pass

            async def asr_to_client():
                try:
                    async for message in asr_ws:
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)
                except Exception:
                    pass

            await asyncio.gather(client_to_asr(), asr_to_client())

    except Exception as exc:
        logger.error("WebSocket proxy error: %s", exc)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
