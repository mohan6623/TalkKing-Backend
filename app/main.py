"""TalkKing API — FastAPI application factory."""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Sentry if DSN is configured
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT, traces_sample_rate=0.1)
    except Exception as e:
        logger.warning("Failed to initialize Sentry: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup/shutdown logic."""
    # Startup: nothing yet (Redis pool is created on import)
    yield
    # Shutdown: close Redis pool
    try:
        from app.core.redis_client import get_redis_pool
        pool = get_redis_pool()
        await pool.aclose()
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
    max_age=600,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check endpoint — no authentication required."""
    checks = {"redis": "unknown", "supabase": "unknown"}

    try:
        from app.core.redis_client import get_redis_pool
        await get_redis_pool().ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    try:
        from app.core.supabase_client import get_supabase
        await asyncio.to_thread(
            lambda: get_supabase().table("profiles").select("id").limit(1).execute()
        )
        checks["supabase"] = "ok"
    except Exception:
        checks["supabase"] = "unavailable"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"

    return {
        "status": overall,
        "service": "talkking-api",
        "env": settings.ENVIRONMENT,
        "checks": checks,
    }
