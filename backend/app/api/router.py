from fastapi import APIRouter

from app.api.routes import resume, runs, profile

api_router = APIRouter()
api_router.include_router(resume.router, prefix="/resume", tags=["resume"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
