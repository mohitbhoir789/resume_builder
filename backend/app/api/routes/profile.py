from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import IngestRequest, IngestResponse
from app.services.ingest import IngestService

router = APIRouter()
service = IngestService()


@router.post("/ingest", response_model=IngestResponse)
def ingest_profile(payload: IngestRequest, request: Request) -> IngestResponse:
    try:
        user_id = getattr(request.state, "user_id", None)
        if user_id and payload.user_id != user_id:
            raise HTTPException(status_code=403, detail="forbidden")
        return service.ingest(payload)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=500, detail=str(exc)) from exc
