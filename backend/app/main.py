import logging
import os
import shutil
from typing import Callable

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.services.ratelimit import RateLimiter


def create_app() -> FastAPI:
    configure_logging()
    ensure_tool_paths()
    app = FastAPI(title="RAG ATS Resume Generator", version="0.1.0")

    # In dev allow all; tighten in prod with config
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)
    app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)

    app.include_router(api_router)
    app.add_api_route("/health", health, methods=["GET"], include_in_schema=False)
    return app


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='{"level":"%(levelname)s","time":"%(asctime)s","message":"%(message)s"}',
    )


def ensure_tool_paths() -> None:
    """Prepend common macOS LaTeX/poppler locations so pdflatex/pdfinfo are discoverable."""
    extra_paths = ["/Library/TeX/texbin", "/opt/homebrew/bin"]
    current = os.environ.get("PATH", "")
    new_paths = [p for p in extra_paths if p not in current.split(":")]
    if new_paths:
        os.environ["PATH"] = ":".join(new_paths + [current])


async def auth_middleware(request: Request, call_next: Callable):
    # Auth disabled: allow all requests, set user_id to anon if not provided
    if request.url.path != "/health":
        api_key = request.headers.get("x-api-key") or request.headers.get("authorization")
        user_map = settings.api_keys
        user_id = user_map.get(api_key) if api_key else "anon"
        request.state.user_id = user_id
    return await call_next(request)


limiter = RateLimiter(settings)


async def rate_limit_middleware(request: Request, call_next: Callable):
    # skip health
    if request.url.path == "/health":
        return await call_next(request)
    user_id = getattr(request.state, "user_id", None)
    try:
        limiter.check(request, user_id=user_id)
    except Exception as exc:
        return JSONResponse(status_code=429, content={"detail": str(exc)})
    return await call_next(request)


def health() -> dict:
    pdflatex_ok = shutil.which("pdflatex") is not None
    pdfinfo_ok = shutil.which("pdfinfo") is not None
    ollama_ok = False
    try:
        resp = httpx.get(f"{settings.ollama_url}/api/tags", timeout=2)
        ollama_ok = resp.status_code == 200
    except Exception:
        ollama_ok = False
    return {"status": "ok", "pdflatex": pdflatex_ok, "pdfinfo": pdfinfo_ok, "ollama_available": ollama_ok}


app = create_app()
