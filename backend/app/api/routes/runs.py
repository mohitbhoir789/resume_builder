from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Response

from app.services.orchestrator import Orchestrator

router = APIRouter()
orchestrator = Orchestrator()


@router.get("/{run_id}/artifacts", response_model=List[str])
def list_artifacts(run_id: str) -> List[str]:

    try:
        return orchestrator.store.list_artifacts(run_id)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{run_id}/audit")
def get_audit(run_id: str) -> Response:

    artifacts = orchestrator.store.list_artifacts(run_id)
    audit = [p for p in artifacts if p.endswith("audit.json")]
    if not audit:
        raise HTTPException(status_code=404, detail="audit not found")
    try:
        data = orchestrator.store.get_artifact(audit[0])
        return Response(content=data, media_type="application/json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="audit not found")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{run_id}/pdf")
def get_pdf(run_id: str) -> Response:

    artifacts = orchestrator.store.list_artifacts(run_id)
    pdfs = [p for p in artifacts if p.endswith(".pdf")]
    if not pdfs:
        raise HTTPException(status_code=404, detail="pdf not found")
    try:
        data = orchestrator.store.get_artifact(pdfs[0])
        return Response(content=data, media_type="application/pdf")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="pdf not found")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=500, detail=str(exc)) from exc
