import uuid
from typing import Dict, Optional

from app.models.schemas import (
    ResumeRequest,
    ResumeResponse,
    ScoreResponse,
    WorkflowStatus,
)
from app.services.pipeline import Pipeline


class Orchestrator:
    """
    Simplified single-user orchestrator.
    """

    def __init__(self) -> None:
        self.pipeline = Pipeline()
        self.store = self.pipeline.store
        self.runs: Dict[str, WorkflowStatus] = {}

    async def run(self, payload: ResumeRequest) -> ResumeResponse:
        run_id = payload.run_id or str(uuid.uuid4())
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
            notes="Generated via deterministic ATS pipeline.",
            extraction=content.extraction,
            mapping=content.mapping,
            score_detail=content.score_detail,
            optimizer=content.optimizer,
            assembler=content.assembler,
            renderer=content.renderer,
        )

    async def score_only(self, payload: ResumeRequest) -> ScoreResponse:
        score = await self.pipeline.score(payload.job, payload.profile)
        return score

    def get_status(self, run_id: str) -> Optional[WorkflowStatus]:
        return self.runs.get(run_id)
