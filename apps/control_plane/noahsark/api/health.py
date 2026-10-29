from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import settings

router = APIRouter()

def _db_state() -> str:
    return "configured" if settings.database_url else "not_configured"

@router.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "db": _db_state(),
        "env": settings.app_env,
        "version": "0.1.0",
    }

@router.get("/readyz")
def readyz():
    state = _db_state()
    if state != "configured":
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": state, "reason": "DATABASE_URL is not configured"},
        )
    return {"status": "ready", "db": state}
