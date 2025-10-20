from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .models import TicketStatus, UserRole


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    username: str
    role: UserRole


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole


class UserOut(UserBase):
    id: int
    created_at: datetime


class ClientIn(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None


class ClientOut(ClientIn):
    id: int
    created_at: datetime


class TicketCreatePublic(BaseModel):
    title: str
    description: str
    client: ClientIn


class TicketAssignIn(BaseModel):
    worker_id: int


class TicketBase(BaseModel):
    title: str
    description: str
    status: TicketStatus
    viewed: bool | None = None


class TicketOut(TicketBase):
    id: int
    client: ClientOut
    worker: Optional[UserOut] = None
    created_at: datetime
    updated_at: datetime
    assigned_at: Optional[datetime] = None
    in_progress_at: Optional[datetime] = None
    done_at: Optional[datetime] = None
    requester_ip: Optional[str] = None
    requester_ua: Optional[str] = None


class TicketsListOut(BaseModel):
    items: list[TicketOut]
    total: int = Field(ge=0, default=0)
    page: int
    size: int


class TicketViewedUpdate(BaseModel):
    viewed: bool


