"""TalkKing API — FastAPI application factory."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup/shutdown logic."""
    # Startup: nothing yet (Redis pool is created on import)
    yield
    # Shutdown: close Redis pool
    try:
        from app.core.redis_client import redis_pool
        await redis_pool.aclose()
    except Exception:
        pass


app = FastAPI(
    title="TalkKing API",
    version="1.0.0",
    description="AI-driven communication coaching platform",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check endpoint — no authentication required."""
    return {
        "status": "ok",
        "service": "talkking-api",
        "env": settings.ENVIRONMENT,
    }
