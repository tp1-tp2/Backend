from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TokenInvalidError
from app.db.session import get_db
from app.services.auth_service import AuthService


async def get_current_user(
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Decodes the JWT locally — unlike the real api-gateway, which round-trips
    to auth-service, the monolith has no separate service to call. This is the
    architectural point of contrast, not an oversight.
    """
    if not authorization.startswith("Bearer "):
        raise TokenInvalidError("Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    auth_service = AuthService(session)
    return await auth_service.validate_token(token)
