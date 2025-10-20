import random
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..db import get_db
from ..models import User, UserRole, Client, Ticket, TicketStatus
from ..security import get_current_user, require_role, hash_password


router = APIRouter(prefix="/admin/seed", tags=["admin-seed"])


@router.post("/")
async def seed_disabled():
    return {"detail": "disabled"}


@router.post("/faker")
async def faker_disabled():
    return {"detail": "disabled"}


@router.post("/reset_and_seed")
async def reset_and_seed_disabled():
    return {"detail": "disabled"}


@router.post("/reset")
async def reset_all(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    await require_role(current_user, (UserRole.admin,))
    # delete tickets and clients
    await db.execute(delete(Ticket))
    await db.execute(delete(Client))
    # delete workers only (keep admins)
    await db.execute(delete(User).where(User.role == UserRole.worker))
    await db.commit()
    return {"status": "ok"}


@router.post("/only_new")
async def only_new_disabled():
    return {"detail": "disabled"}


