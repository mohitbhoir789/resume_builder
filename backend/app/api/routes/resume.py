from fastapi import APIRouter, HTTPException

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
async def generate_resume(payload: ResumeRequest) -> ResumeResponse:
    try:
        return await orchestrator.run(payload)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/score", response_model=ScoreResponse)
async def score_resume(payload: ResumeRequest) -> ScoreResponse:
    return await orchestrator.score_only(payload)


@router.get("/status/{run_id}", response_model=WorkflowStatus)
async def get_status(run_id: str) -> WorkflowStatus:
    status = orchestrator.get_status(run_id)
    if not status:
        raise HTTPException(status_code=404, detail="run not found")
    return status
