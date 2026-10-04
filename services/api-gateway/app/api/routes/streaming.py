import asyncio
import logging

import httpx
import websockets
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.api.dependencies import build_http_client
from app.core import token_validator
from app.core.config import settings

router = APIRouter(tags=["streaming"])
logger = logging.getLogger(__name__)


async def _validate_token(token: str, http: httpx.AsyncClient) -> bool:
    try:
        await token_validator.validate(token, http)
        return True
    except Exception:
        return False


@router.websocket("/ws/stream")
async def ws_proxy(
    websocket: WebSocket,
    token: str = Query(...),
    sample_rate: int = Query(16000),
    encoding: str = Query("pcm"),
):
    http = getattr(websocket.app.state, "http", None)
    if http is None:
        async with build_http_client() as tmp_http:
            valid = await _validate_token(token, tmp_http)
    else:
        valid = await _validate_token(token, http)
    if not valid:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    asr_ws_url = (
        settings.asr_service_url.replace("http://", "ws://").replace("https://", "wss://")
        + f"/ws/stream?token={token}&sample_rate={sample_rate}&encoding={encoding}"
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
