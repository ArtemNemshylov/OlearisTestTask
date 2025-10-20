from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .models import TicketStatus, UserRole


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="Username")
    password: str = Field(..., min_length=1, max_length=100, description="Password")


class UserBase(BaseModel):
    username: str
    role: UserRole


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    password: str = Field(..., min_length=6, max_length=100, description="Password (6-100 characters)")
    role: UserRole


class UserOut(UserBase):
    id: int
    created_at: datetime


class ClientIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Client name")
    email: EmailStr = Field(..., description="Valid email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number (optional)")


class ClientOut(ClientIn):
    id: int
    created_at: datetime


class TicketCreatePublic(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Ticket title")
    description: str = Field(..., min_length=1, max_length=1000, description="Ticket description")
    client: ClientIn


class TicketAssignIn(BaseModel):
    worker_id: int = Field(..., gt=0, description="Valid worker ID")


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


