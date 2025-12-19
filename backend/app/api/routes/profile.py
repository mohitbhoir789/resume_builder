from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import IngestResponse
from app.services.ingest import IngestService

router = APIRouter()
service = IngestService()


class ResumeTextRequest(BaseModel):
    resume_text: str


@router.post("/ingest", response_model=IngestResponse)
def ingest_profile(
    resume_file: Optional[UploadFile] = File(default=None),
) -> IngestResponse:
    try:
        if not resume_file:
            raise HTTPException(status_code=400, detail="Provide resume_file (pdf)")
        return service.ingest_pdf(resume_file)
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ingest-text", response_model=IngestResponse)
def ingest_profile_text(
    request: ResumeTextRequest,
) -> IngestResponse:
    try:
        if not request.resume_text or not request.resume_text.strip():
            raise HTTPException(status_code=400, detail="Provide non-empty resume_text")
        return service.ingest_text(request.resume_text)
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=500, detail=str(exc)) from exc
