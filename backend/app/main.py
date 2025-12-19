import logging
import os
import shutil
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    configure_logging()
    ensure_tool_paths()
    app = FastAPI(title="RAG ATS Resume Generator", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.add_api_route("/health", health, methods=["GET"], include_in_schema=False)
    return app


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='{"level":"%(levelname)s","time":"%(asctime)s","message":"%(message)s"}',
    )


def ensure_tool_paths() -> None:
    extra_paths = ["/Library/TeX/texbin", "/opt/homebrew/bin"]
    current = os.environ.get("PATH", "")
    new_paths = [p for p in extra_paths if p not in current.split(":")]
    if new_paths:
        os.environ["PATH"] = ":".join(new_paths + [current])


def health() -> dict:
    pdflatex_ok = shutil.which("pdflatex") is not None
    pdfinfo_ok = shutil.which("pdfinfo") is not None
    gemini_ok = False
    try:
        gemini_ok = bool(settings.gemini_api_key)
        if gemini_ok:
            # lightweight check: ensure env key present; no API call to avoid cost
            gemini_ok = True
    except Exception:
        gemini_ok = False
    return {"status": "ok", "pdflatex": pdflatex_ok, "pdfinfo": pdfinfo_ok, "gemini_available": gemini_ok}


app = create_app()
