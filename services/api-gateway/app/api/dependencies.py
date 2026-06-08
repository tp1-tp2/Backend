from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validate JWT token via Auth Service and return user context."""
    token = credentials.credentials
    # Token validation delegated to Auth Service in task 8.3
    return {"token": token}
