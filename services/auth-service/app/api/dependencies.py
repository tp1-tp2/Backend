from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from fastapi import Depends


async def get_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    return db
