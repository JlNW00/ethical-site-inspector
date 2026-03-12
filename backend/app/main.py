from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.audits import router as audits_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.seed_service import ensure_seeded_demo


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.seeded_demo_audit_id = ensure_seeded_demo(SessionLocal)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/artifacts", StaticFiles(directory=settings.local_storage_root), name="artifacts")
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(audits_router, prefix=settings.api_prefix)
