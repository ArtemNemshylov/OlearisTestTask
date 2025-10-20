from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..schemas import LoginIn, TokenOut, UserOut
from ..security import create_access_token, verify_password, get_current_user
from ..core.config import settings
from fastapi import Form
from fastapi import Body
from ..models import User, UserRole
from ..security import require_role


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut, status_code=200)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut(id=current_user.id, username=current_user.username, role=current_user.role, created_at=current_user.created_at)


@router.post("/token", response_model=TokenOut, status_code=200)
async def token_client_credentials(
    grant_type: str = Form(..., description="OAuth2 grant type"),
    client_id: str = Form(..., description="OAuth2 client ID"),
    client_secret: str = Form(..., description="OAuth2 client secret"),
):
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
    if client_id != settings.oauth_client_id or client_secret != settings.oauth_client_secret:
        raise HTTPException(status_code=401, detail="invalid_client")
    # issue a token with role=admin for automation; adjust as needed
    token = create_access_token({"sub": client_id, "role": "admin"})
    return TokenOut(access_token=token)


@router.post("/exchange_view_token", response_model=TokenOut)
async def exchange_view_token(
    vt: str = Body(..., embed=True),
):
    # kept for compatibility; disable by default
    raise HTTPException(status_code=404, detail="disabled")


@router.post("/request_view_token", response_model=TokenOut)
async def request_view_token(current_user: User = Depends(get_current_user)):
    # only admins can mint a short-lived view token
    await require_role(current_user, (UserRole.admin,))
    token = create_access_token({"sub": current_user.username, "role": "admin"}, expires_minutes=5)
    return TokenOut(access_token=token)


