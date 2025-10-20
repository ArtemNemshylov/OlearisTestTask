from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User, UserRole, Ticket, TicketStatus
from ..schemas import UserCreate, UserOut
from ..security import get_current_user, hash_password, require_role


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserOut, status_code=201)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_role(current_user, (UserRole.admin,))
    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(username=payload.username, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut(id=user.id, username=user.username, role=user.role, created_at=user.created_at)


@router.get("/", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    await require_role(current_user, (UserRole.admin,))
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [UserOut(id=u.id, username=u.username, role=u.role, created_at=u.created_at) for u in users]


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    await require_role(current_user, (UserRole.admin,))
    # Check if user exists
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Reassign tickets: unassign worker and set status to new for admin review
    await db.execute(
        update(Ticket)
        .where(Ticket.worker_id == user_id)
        .values(worker_id=None, status=TicketStatus.new)
    )
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    return None


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_role(current_user, (UserRole.admin,))
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.username = payload.username
    user.role = payload.role
    if payload.password:
        user.password_hash = hash_password(payload.password)
    await db.commit()
    await db.refresh(user)
    return UserOut(id=user.id, username=user.username, role=user.role, created_at=user.created_at)


