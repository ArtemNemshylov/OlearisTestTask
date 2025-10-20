from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, join

from ..db import get_db
from fastapi import Request
from ..models import Client, Ticket, TicketStatus
from ..schemas import TicketCreatePublic, TicketOut, ClientOut, UserOut


router = APIRouter(prefix="/public", tags=["public"])


@router.post("/tickets", response_model=TicketOut, status_code=201)
async def create_ticket(payload: TicketCreatePublic, request: Request, db: AsyncSession = Depends(get_db)):
    # prevent exact duplicates by title, description, and client email
    dup_q = (
        select(Ticket.id)
        .select_from(join(Ticket, Client, Ticket.client_id == Client.id))
        .where(
            Ticket.title == payload.title,
            Ticket.description == payload.description,
            Client.email == payload.client.email,
        )
        .limit(1)
    )
    if (await db.execute(dup_q)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Duplicate ticket detected")
    client = Client(name=payload.client.name, email=payload.client.email, phone=payload.client.phone)
    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        status=TicketStatus.new,
        requester_ip=request.client.host if request.client else None,
        requester_ua=request.headers.get("user-agent"),
    )
    ticket.client = client
    db.add_all([client, ticket])
    await db.commit()
    await db.refresh(ticket)
    await db.refresh(client)

    return TicketOut(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        client=ClientOut(id=client.id, name=client.name, email=client.email, phone=client.phone, created_at=client.created_at),
        worker=None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        assigned_at=ticket.assigned_at,
        in_progress_at=ticket.in_progress_at,
        done_at=ticket.done_at,
        requester_ip=ticket.requester_ip,
        requester_ua=ticket.requester_ua,
    )


