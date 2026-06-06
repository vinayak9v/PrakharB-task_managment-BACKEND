"""
AI-PS Platform — Main Application
FastAPI + MySQL + SQLAlchemy ORM
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.init_db import init_db
from app.services.scheduler import start_scheduler
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup:
    1. Create all DB tables automatically via ORM
    2. Create Super Admin if not exists
    3. Start background scheduler (reminders, EOD, daily to-do)
    """
    logger.info("🚀 Starting AI-PS Platform...")
    init_db()           # ← tables auto-created here
    start_scheduler()   # ← cron jobs start here
    logger.info("✅ AI-PS Platform is ready!")
    yield
    logger.info("👋 Shutting down AI-PS Platform...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Personal Secretary — Executive Assistant & Operations Manager for Prakhar Bagora",
    docs_url="/docs",       # Swagger UI at http://localhost:8000/docs
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/")
def root():
    return {
        "platform": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "message": "AI-PS Platform is active. Jai Hind! 🇮🇳"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
