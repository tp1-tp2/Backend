import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


async def get_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    return db


async def get_http_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client
