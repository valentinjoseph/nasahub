import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.routes import analytics_router
from api.schemas import HealthResponse
from core.config import (
    API_AUTH_TOKEN,
    API_ENABLE_DOCS,
    API_REQUIRE_AUTH,
    API_TITLE,
    API_VERSION,
)
from db.deps import get_db
from db.models import IngestionRun
from db.session import engine

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
DASHBOARD_INDEX = FRONTEND_DIR / "index.html"

docs_url = "/docs" if API_ENABLE_DOCS else None
redoc_url = "/redoc" if API_ENABLE_DOCS else None
openapi_url = "/openapi.json" if API_ENABLE_DOCS else None

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

EXEMPT_AUTH_PATHS = {"/", "/dashboard", "/health", "/health/live", "/health/ready"}


def path_requires_auth(path: str) -> bool:
    return path not in EXEMPT_AUTH_PATHS and not path.startswith("/dashboard-assets/")


def request_has_valid_auth(headers: dict, expected_token: str | None) -> bool:
    if not expected_token:
        return False

    api_key = headers.get("x-api-key")
    if api_key == expected_token:
        return True

    authorization = headers.get("authorization", "")
    if authorization == f"Bearer {expected_token}":
        return True

    return False


def get_request_id(headers: dict) -> str:
    return headers.get("x-request-id") or str(uuid4())


def build_access_log_payload(
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
) -> dict:
    return {
        "request_id": request_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
    }


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = get_request_id(request.headers)
    started_at = perf_counter()
    response = await call_next(request)
    duration_ms = (perf_counter() - started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    print(
        json.dumps(
            build_access_log_payload(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        ),
        flush=True,
    )
    return response


@app.middleware("http")
async def enforce_api_auth(request: Request, call_next):
    if API_REQUIRE_AUTH and path_requires_auth(request.url.path):
        if not request_has_valid_auth(request.headers, API_AUTH_TOKEN):
            response = JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized"},
            )
            response.headers["X-Request-ID"] = get_request_id(request.headers)
            return response
    return await call_next(request)


def database_ready() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard", status_code=307)


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(DASHBOARD_INDEX)


@app.get("/health/live", response_model=HealthResponse)
def health_live():
    return {
        "status": "ok",
        "database": "unknown",
    }


@app.get("/health/ready", response_model=HealthResponse)
def health_ready():
    db_ok = database_ready()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
    }


@app.get("/health", response_model=HealthResponse)
def health():
    return health_ready()


@app.get("/ingestion-runs")
def list_ingestion_runs(db: Session = Depends(get_db)):
    runs = db.query(IngestionRun).order_by(IngestionRun.id.desc()).all()

    return [
        {
            "id": run.id,
            "source": run.source,
            "status": run.status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        }
        for run in runs
    ]


app.include_router(analytics_router)
app.mount("/dashboard-assets", StaticFiles(directory=str(FRONTEND_DIR)), name="dashboard-assets")
