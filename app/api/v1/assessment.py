"""Assessment routes — POST /demo/assess (public, no auth required)."""
from fastapi import APIRouter, HTTPException, UploadFile, File

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/assess")
async def demo_assess(
    audio: UploadFile = File(...),
):
    """Run an anonymous demo assessment on uploaded audio.

    No authentication required. Returns a teaser result.
    Implementation will call AI orchestrator in a later task.
    """
    # TODO: Implement with AI orchestrator (Task 10)
    raise HTTPException(status_code=501, detail="Not yet implemented")
