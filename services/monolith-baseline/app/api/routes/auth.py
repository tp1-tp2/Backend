from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, RegistrationResponse, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=RegistrationResponse, status_code=201)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_db)):
    return await AuthService(session).register(body.email, body.password, body.full_name)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_db)):
    return await AuthService(session).login(body.email, body.password)


@router.post("/logout", status_code=204)
async def logout(authorization: str = Header(default=""), session: AsyncSession = Depends(get_db)):
    token = authorization.removeprefix("Bearer ").strip()
    await AuthService(session).logout(token)
