from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy import select, func, update
from datetime import datetime
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Ticket, TicketStatus, User, UserRole
from ..schemas import TicketsListOut, TicketOut, ClientOut, UserOut, TicketViewedUpdate
from ..security import get_current_user, require_role


router = APIRouter(prefix="/tickets", tags=["tickets"])
@router.get("/stats", status_code=200)
async def tickets_stats(
    worker_id: int = Query(..., gt=0, description="Worker ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_role(current_user, (UserRole.admin,))
    # assigned new = status new and has this worker
    assigned_new = (
        await db.execute(
            select(func.count()).select_from(Ticket).where(
                Ticket.worker_id == worker_id, Ticket.status == TicketStatus.new
            )
        )
    ).scalar() or 0
    in_progress = (
        await db.execute(
            select(func.count()).select_from(Ticket).where(
                Ticket.worker_id == worker_id, Ticket.status == TicketStatus.in_progress
            )
        )
    ).scalar() or 0
    return {"assigned": assigned_new, "in_progress": in_progress}



@router.get("/", response_model=TicketsListOut, status_code=200)
async def list_tickets(
    page: int = Query(1, ge=1, description="Page number (1+)"),
    size: int = Query(10, ge=1, le=100, description="Page size (1-100)"),
    search: str | None = Query(None, max_length=100, description="Search by title"),
    status: TicketStatus | None = Query(None, description="Filter by status"),
    worker_id: int | None = Query(None, gt=0, description="Filter by worker ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_role(current_user, (UserRole.admin, UserRole.worker))

    query = (
        select(Ticket)
        .options(selectinload(Ticket.client))
        .options(selectinload(Ticket.worker))
    )
    if search:
        query = query.where(Ticket.title.ilike(f"%{search}%"))
    if status:
        query = query.where(Ticket.status == status)
    if current_user.role == UserRole.worker:
        query = query.where(Ticket.worker_id == current_user.id)
    else:
        if worker_id is not None:
            query = query.where(Ticket.worker_id == worker_id)

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    items = (await db.execute(query.order_by(Ticket.created_at.desc()).offset((page - 1) * size).limit(size))).scalars().all()

    def to_out(t: Ticket) -> TicketOut:
        worker_out = (
            UserOut(id=t.worker.id, username=t.worker.username, role=t.worker.role, created_at=t.worker.created_at)
            if t.worker
            else None
        )
        client = t.client
        return TicketOut(
            id=t.id,
            title=t.title,
            description=t.description,
            status=t.status,
            client=ClientOut(id=client.id, name=client.name, email=client.email, phone=client.phone, created_at=client.created_at),
            worker=worker_out,
            created_at=t.created_at,
            updated_at=t.updated_at,
            assigned_at=t.assigned_at,
            in_progress_at=t.in_progress_at,
            done_at=t.done_at,
            requester_ip=t.requester_ip,
            requester_ua=t.requester_ua,
        )

    return TicketsListOut(items=[to_out(i) for i in items], total=total, page=page, size=size)


@router.post("/{ticket_id}/viewed", response_model=TicketOut, status_code=200)
async def mark_viewed(
    ticket_id: int = Path(..., gt=0, description="Ticket ID"),
    payload: TicketViewedUpdate = Body(..., description="Viewed status update"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_role(current_user, (UserRole.admin, UserRole.worker))
    ticket = (
        await db.execute(
            select(Ticket)
            .options(selectinload(Ticket.client))
            .options(selectinload(Ticket.worker))
            .where(Ticket.id == ticket_id)
        )
    ).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == UserRole.worker and ticket.worker_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot modify other worker's ticket")
    await db.execute(update(Ticket).where(Ticket.id == ticket_id).values(viewed=payload.viewed))
    await db.commit()
    ticket = (
        await db.execute(
            select(Ticket)
            .options(selectinload(Ticket.client))
            .options(selectinload(Ticket.worker))
            .where(Ticket.id == ticket_id)
        )
    ).scalar_one()
    client = ticket.client
    worker = ticket.worker
    worker_out = (
        UserOut(id=worker.id, username=worker.username, role=worker.role, created_at=worker.created_at)
        if worker
        else None
    )
    return TicketOut(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        viewed=ticket.viewed,
        client=ClientOut(id=client.id, name=client.name, email=client.email, phone=client.phone, created_at=client.created_at),
        worker=worker_out,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.post("/{ticket_id}/assign", response_model=TicketOut, status_code=200)
async def assign_ticket(
    ticket_id: int = Path(..., gt=0, description="Ticket ID"),
    worker_id: int = Body(..., gt=0, description="Worker ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_role(current_user, (UserRole.admin,))
    ticket = (
        await db.execute(
            select(Ticket)
            .options(selectinload(Ticket.client))
            .options(selectinload(Ticket.worker))
            .where(Ticket.id == ticket_id)
        )
    ).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    # Ensure worker exists and is a worker role
    worker = (
        await db.execute(select(User).where(User.id == worker_id, User.role == UserRole.worker))
    ).scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=400, detail="Worker not found or not a worker")

    await db.execute(
        update(Ticket)
        .where(Ticket.id == ticket_id)
        .values(worker_id=worker_id, updated_at=datetime.utcnow(), assigned_at=datetime.utcnow())
    )
    await db.commit()
    ticket = (
        await db.execute(
            select(Ticket)
            .options(selectinload(Ticket.client))
            .options(selectinload(Ticket.worker))
            .where(Ticket.id == ticket_id)
        )
    ).scalar_one()
    client = ticket.client
    worker = ticket.worker
    worker_out = (
        UserOut(id=worker.id, username=worker.username, role=worker.role, created_at=worker.created_at)
        if worker
        else None
    )
    return TicketOut(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        assigned_at=ticket.assigned_at,
        in_progress_at=ticket.in_progress_at,
        done_at=ticket.done_at,
        requester_ip=ticket.requester_ip,
        requester_ua=ticket.requester_ua,
        client=ClientOut(id=client.id, name=client.name, email=client.email, phone=client.phone, created_at=client.created_at),
        worker=worker_out,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.post("/{ticket_id}/status", response_model=TicketOut, status_code=200)
async def update_status(
    ticket_id: int = Path(..., gt=0, description="Ticket ID"),
    new_status: TicketStatus = Body(..., description="New ticket status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_role(current_user, (UserRole.admin, UserRole.worker))
    ticket = (
        await db.execute(
            select(Ticket)
            .options(selectinload(Ticket.client))
            .options(selectinload(Ticket.worker))
            .where(Ticket.id == ticket_id)
        )
    ).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if current_user.role == UserRole.worker and ticket.worker_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot modify other worker's ticket")
    set_vals = {"status": new_status}
    if new_status == TicketStatus.in_progress:
        set_vals["in_progress_at"] = datetime.utcnow()
    if new_status == TicketStatus.done:
        set_vals["done_at"] = datetime.utcnow()
    await db.execute(update(Ticket).where(Ticket.id == ticket_id).values(**set_vals))
    await db.commit()
    ticket = (
        await db.execute(
            select(Ticket)
            .options(selectinload(Ticket.client))
            .options(selectinload(Ticket.worker))
            .where(Ticket.id == ticket_id)
        )
    ).scalar_one()
    client = ticket.client
    worker = ticket.worker
    worker_out = (
        UserOut(id=worker.id, username=worker.username, role=worker.role, created_at=worker.created_at)
        if worker
        else None
    )
    return TicketOut(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        assigned_at=ticket.assigned_at,
        in_progress_at=ticket.in_progress_at,
        done_at=ticket.done_at,
        requester_ip=ticket.requester_ip,
        requester_ua=ticket.requester_ua,
        client=ClientOut(id=client.id, name=client.name, email=client.email, phone=client.phone, created_at=client.created_at),
        worker=worker_out,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


