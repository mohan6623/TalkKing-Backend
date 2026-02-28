"""API router aggregation — collects all v1 route modules."""
from fastapi import APIRouter
from app.api.v1 import auth, users, sessions, feedback, progress, history, assessment

api_router = APIRouter()

# Register all v1 routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(sessions.router)
api_router.include_router(feedback.router)
api_router.include_router(progress.router)
api_router.include_router(history.router)
api_router.include_router(assessment.router)
