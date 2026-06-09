from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.schemas.auth import (
    BlocklistTokenRequest,
    CreateCredentialRequest,
    ValidateTokenRequest,
    ValidateTokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/internal/auth", tags=["internal"])


def _svc(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session)


@router.post("/credentials", status_code=201)
async def create_credential(
    body: CreateCredentialRequest, svc: AuthService = Depends(_svc)
):
    await svc.create_credential(body.user_id, body.email, body.password_hash)
    return {"status": "created"}


@router.post("/validate-token", response_model=ValidateTokenResponse)
async def validate_token(
    body: ValidateTokenRequest, svc: AuthService = Depends(_svc)
):
    return await svc.validate_token(body.token)


@router.post("/blocklist-token", status_code=204)
async def blocklist_token(
    body: BlocklistTokenRequest, svc: AuthService = Depends(_svc)
):
    await svc.blocklist_token(body.token, body.expires_at)
