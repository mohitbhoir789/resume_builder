from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import (
    ResumeRequest,
    ResumeResponse,
    ScoreResponse,
    WorkflowStatus,
)
from app.services.orchestrator import Orchestrator

router = APIRouter()
orchestrator = Orchestrator()


@router.get("/health", response_model=dict)
def health() -> dict:
    return {"status": "ok"}


@router.post("/generate", response_model=ResumeResponse)
async def generate_resume(payload: ResumeRequest, request: Request) -> ResumeResponse:
    try:
        user_id = getattr(request.state, "user_id", None)
        return await orchestrator.run(payload, user_id=user_id)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/score", response_model=ScoreResponse)
async def score_resume(payload: ResumeRequest, request: Request) -> ScoreResponse:
    user_id = getattr(request.state, "user_id", None)
    return await orchestrator.score_only(payload, user_id=user_id)


@router.get("/status/{run_id}", response_model=WorkflowStatus)
async def get_status(run_id: str, request: Request) -> WorkflowStatus:
    user_id = getattr(request.state, "user_id", None)
    status = orchestrator.get_status(run_id, user_id=user_id)
    if not status:
        raise HTTPException(status_code=404, detail="run not found")
    return status
