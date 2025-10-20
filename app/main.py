from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, public, users, tickets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .db import AsyncSessionLocal
from .models import User, UserRole
from .security import hash_password
import os
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


def create_app() -> FastAPI:
    app = FastAPI(title="Mini-CRM Repair Requests")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(public.router)
    app.include_router(users.router)
    app.include_router(tickets.router)
    # seed/admin routes removed for production cleanliness

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail or exc.__class__.__name__, "status": exc.status_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Validation error",
                "status": 400,
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "status": 500},
        )

    @app.on_event("startup")
    async def seed_default_users():
        # Optional seeding via env vars; idempotent
        admin_username = os.getenv("ADMIN_USERNAME")
        admin_password = os.getenv("ADMIN_PASSWORD")
        worker_username = os.getenv("WORKER_USERNAME")
        worker_password = os.getenv("WORKER_PASSWORD")
        async with AsyncSessionLocal() as db:  # type: AsyncSession
            if admin_username and admin_password:
                exists = (await db.execute(select(User).where(User.username == admin_username))).scalar_one_or_none()
                if not exists:
                    db.add(
                        User(
                            username=admin_username,
                            password_hash=hash_password(admin_password),
                            role=UserRole.admin,
                        )
                    )
                    await db.commit()
            if worker_username and worker_password:
                exists = (await db.execute(select(User).where(User.username == worker_username))).scalar_one_or_none()
                if not exists:
                    db.add(
                        User(
                            username=worker_username,
                            password_hash=hash_password(worker_password),
                            role=UserRole.worker,
                        )
                    )
                    await db.commit()

    return app


app = create_app()


