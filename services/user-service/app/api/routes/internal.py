import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_http_client, get_session
from app.schemas.user import InternalUserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/internal/users", tags=["internal"])


def _svc(
    session: AsyncSession = Depends(get_session),
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> UserService:
    return UserService(session, http_client)


@router.get("/{user_id}", response_model=InternalUserResponse)
async def get_user(user_id: str, svc: UserService = Depends(_svc)):
    profile = await svc.get_profile(user_id)
    return InternalUserResponse(
        user_id=profile.user_id,
        email=profile.email,
        full_name=profile.full_name,
    )
