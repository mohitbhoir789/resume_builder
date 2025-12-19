from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.models.schemas import IngestResponse
from app.services.ingest import IngestService

router = APIRouter()
service = IngestService()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_profile(
    resume_file: UploadFile | None = File(default=None),
    resume_text: str | None = Form(default=None),
) -> IngestResponse:
    try:
        if resume_file and resume_text:
            raise HTTPException(status_code=400, detail="Provide either resume_file or resume_text, not both")
        if not resume_file and not resume_text:
            raise HTTPException(status_code=400, detail="Provide resume_file (pdf) or resume_text")
        if resume_file:
            return service.ingest_pdf(resume_file)
        return service.ingest_text(resume_text or "")
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=500, detail=str(exc)) from exc
