import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_http_client, get_session
from app.schemas.user import (
    EmailChangeRequestSchema,
    EmailChangeVerifyRequest,
    RegistrationRequest,
    RegistrationResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(tags=["users"])


def _svc(
    session: AsyncSession = Depends(get_session),
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> UserService:
    return UserService(session, http_client)


@router.post("/api/v1/auth/register", response_model=RegistrationResponse, status_code=201)
async def register(
    body: RegistrationRequest,
    background_tasks: BackgroundTasks,
    svc: UserService = Depends(_svc),
):
    return await svc.register(body.email, body.password, body.full_name, background_tasks)


@router.get("/api/v1/users/profile", response_model=UserResponse)
async def get_profile(
    x_user_id: str = Header(..., alias="X-User-Id"),
    svc: UserService = Depends(_svc),
):
    return await svc.get_profile(x_user_id)


@router.put("/api/v1/users/profile", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
    svc: UserService = Depends(_svc),
):
    return await svc.update_profile(x_user_id, body)


@router.post("/api/v1/users/email-change", status_code=204)
async def initiate_email_change(
    body: EmailChangeRequestSchema,
    background_tasks: BackgroundTasks,
    x_user_id: str = Header(..., alias="X-User-Id"),
    svc: UserService = Depends(_svc),
):
    await svc.initiate_email_change(x_user_id, body.new_email, background_tasks)


@router.post("/api/v1/users/email-change/verify", status_code=204)
async def verify_email_change(
    body: EmailChangeVerifyRequest,
    svc: UserService = Depends(_svc),
):
    await svc.verify_email_change(body.token, body.link_type)
