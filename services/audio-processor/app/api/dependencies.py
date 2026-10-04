import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


async def get_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    return db


async def get_http_client(request: Request) -> httpx.AsyncClient:
    # Shared keep-alive pool created in main.py's lifespan (was one client,
    # and one TCP handshake, per request).
    shared = getattr(request.app.state, "http", None)
    if shared is not None:
        yield shared
        return
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client
