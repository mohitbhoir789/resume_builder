import uuid
from typing import Dict, Optional

from fastapi import HTTPException

from app.models.schemas import (
    ProfileInput,
    ResumeContent,
    ResumeRequest,
    ResumeResponse,
    ScoreResponse,
    WorkflowStatus,
)
from app.services.pipeline import Pipeline


class Orchestrator:
    """
    Lightweight in-memory orchestrator placeholder.
    Replace with durable workflows (Temporal/Prefect) for production.
    """

    def __init__(self) -> None:
        self.pipeline = Pipeline()
        self.store = self.pipeline.store
        self.runs: Dict[str, WorkflowStatus] = {}
        self.run_owners: Dict[str, str] = {}

    async def run(self, payload: ResumeRequest, user_id: Optional[str]) -> ResumeResponse:
        run_id = payload.run_id or str(uuid.uuid4())
        self.run_owners[run_id] = user_id or "anon"
        self.runs[run_id] = WorkflowStatus(run_id=run_id, status="running")
        content = await self.pipeline.generate(payload.job, payload.profile, run_id)
        pdf_url = content.pdf_path or (content.renderer.pdf_path if content.renderer else f"/artifacts/{run_id}.pdf")
        self.runs[run_id] = WorkflowStatus(
            run_id=run_id, status="completed", ats_score=content.ats_score, message="ok"
        )
        return ResumeResponse(
            run_id=run_id,
            status="completed",
            ats_score=content.ats_score,
            pdf_url=pdf_url,
            page_count=content.page_count,
            render_attempts=len(content.renderer.render_attempts) if content.renderer else None,
            audit_url=content.audit_path,
            keywords=content.keywords,
            gaps=content.gaps,
            notes="Generated via deterministic ATS pipeline; PDF rendering stub.",
            extraction=content.extraction,
            mapping=content.mapping,
            score_detail=content.score_detail,
            optimizer=content.optimizer,
            assembler=content.assembler,
            renderer=content.renderer,
        )

    async def score_only(self, payload: ResumeRequest, user_id: Optional[str]) -> ScoreResponse:
        # scoring only; no run tracking
        score = await self.pipeline.score(payload.job, payload.profile)
        return score

    def get_status(self, run_id: str, user_id: Optional[str]) -> Optional[WorkflowStatus]:
        owner = self.run_owners.get(run_id)
        if owner and owner != (user_id or "anon"):
            return None
        return self.runs.get(run_id)

    def ensure_owner(self, run_id: str, user_id: Optional[str]) -> None:
        owner = self.run_owners.get(run_id)
        if owner and owner != (user_id or "anon"):
            raise HTTPException(status_code=403, detail="forbidden")
