from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    PasswordRecoveryRequest,
    PasswordResetRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _svc(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, svc: AuthService = Depends(_svc)):
    return await svc.login(body.email, body.password)


@router.post("/logout", status_code=204)
async def logout(body: LogoutRequest, svc: AuthService = Depends(_svc)):
    await svc.logout(body.token)


@router.post("/password-recovery", status_code=204)
async def password_recovery(
    body: PasswordRecoveryRequest, svc: AuthService = Depends(_svc)
):
    await svc.initiate_recovery(body.email)


@router.post("/password-reset", status_code=204)
async def password_reset(
    body: PasswordResetRequest, svc: AuthService = Depends(_svc)
):
    await svc.reset_password(body.token, body.new_password)
