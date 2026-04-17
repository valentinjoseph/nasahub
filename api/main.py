import json
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock
from time import perf_counter, time
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
    ASK_RATE_LIMIT_MAX_REQUESTS,
    API_ENABLE_DOCS,
    API_REQUIRE_AUTH,
    API_TITLE,
    API_VERSION,
    PUBLIC_RATE_LIMIT_MAX_REQUESTS,
    PUBLIC_RATE_LIMIT_WINDOW_SECONDS,
    RATE_LIMIT_ENABLED,
    VIEWER_ACCESS_TOKEN,
)
from db.deps import get_db
from db.models import IngestionRun
from db.session import engine

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
DASHBOARD_INDEX = FRONTEND_DIR / "index.html"
PUBLIC_INDEX = FRONTEND_DIR / "public.html"

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

EXEMPT_AUTH_PATHS = {
    "/",
    "/dashboard",
    "/viewer",
    "/viewer/logout",
    "/health",
    "/health/live",
    "/health/ready",
}
VIEWER_ALLOWED_POST_PATHS = {"/analytics/ask"}
RATE_LIMIT_BUCKETS = {
    "public": defaultdict(deque),
    "ask": defaultdict(deque),
}
RATE_LIMIT_LOCK = Lock()


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


def request_has_valid_viewer_auth(request: Request, expected_token: str | None) -> bool:
    if not expected_token:
        return False
    viewer_header = request.headers.get("x-viewer-token")
    if viewer_header == expected_token:
        return True
    viewer_query = request.query_params.get("access")
    if viewer_query == expected_token:
        return True
    viewer_cookie = request.cookies.get("nasahub_viewer_token")
    if viewer_cookie == expected_token:
        return True
    return False


def viewer_request_is_allowed(method: str, path: str) -> bool:
    if path in EXEMPT_AUTH_PATHS or path.startswith("/dashboard-assets/"):
        return True
    if method == "GET" and path.startswith("/analytics/"):
        return path not in {"/analytics/saved-contexts", "/analytics/pins"}
    if method == "POST" and path in VIEWER_ALLOWED_POST_PATHS:
        return True
    return False


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        first_hop = forwarded_for.split(",")[0].strip()
        if first_hop:
            return first_hop
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def get_rate_limit_scope(method: str, path: str) -> str | None:
    if method == "POST" and path == "/analytics/ask":
        return "ask"
    if path in {"/", "/dashboard", "/viewer", "/viewer/logout"}:
        return "public"
    if path.startswith("/dashboard-assets/"):
        return "public"
    if method == "GET" and path.startswith("/analytics/"):
        return "public"
    return None


def get_rate_limit_max_requests(scope: str) -> int:
    if scope == "ask":
        return ASK_RATE_LIMIT_MAX_REQUESTS
    return PUBLIC_RATE_LIMIT_MAX_REQUESTS


def consume_rate_limit(scope: str, client_ip: str, now: float | None = None) -> tuple[bool, int]:
    timestamp = now if now is not None else time()
    window_start = timestamp - PUBLIC_RATE_LIMIT_WINDOW_SECONDS
    max_requests = get_rate_limit_max_requests(scope)

    with RATE_LIMIT_LOCK:
        bucket = RATE_LIMIT_BUCKETS[scope][client_ip]
        while bucket and bucket[0] <= window_start:
            bucket.popleft()
        if len(bucket) >= max_requests:
            retry_after = max(1, int(bucket[0] + PUBLIC_RATE_LIMIT_WINDOW_SECONDS - timestamp))
            return False, retry_after
        bucket.append(timestamp)
    return True, 0


def get_request_id(headers: dict) -> str:
    return headers.get("x-request-id") or str(uuid4())


def is_secure_request(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    if forwarded_proto:
        return forwarded_proto.split(",")[0].strip() == "https"
    return request.url.scheme == "https"


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
    if request.query_params.get("access") and request_has_valid_viewer_auth(request, VIEWER_ACCESS_TOKEN):
        response.set_cookie(
            key="nasahub_viewer_token",
            value=request.query_params["access"],
            httponly=True,
            secure=is_secure_request(request),
            samesite="lax",
        )
        response.set_cookie(
            key="nasahub_viewer_mode",
            value="1",
            httponly=False,
            secure=is_secure_request(request),
            samesite="lax",
        )
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
        if request_has_valid_auth(request.headers, API_AUTH_TOKEN):
            return await call_next(request)
        if request_has_valid_viewer_auth(request, VIEWER_ACCESS_TOKEN):
            if viewer_request_is_allowed(request.method, request.url.path):
                return await call_next(request)
            response = JSONResponse(
                status_code=403,
                content={"detail": "Viewer access is read-only for this route"},
            )
            response.headers["X-Request-ID"] = get_request_id(request.headers)
            return response
        if not request_has_valid_auth(request.headers, API_AUTH_TOKEN):
            response = JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized"},
            )
            response.headers["X-Request-ID"] = get_request_id(request.headers)
            return response
    return await call_next(request)


@app.middleware("http")
async def enforce_rate_limits(request: Request, call_next):
    if not RATE_LIMIT_ENABLED:
        return await call_next(request)

    if request_has_valid_auth(request.headers, API_AUTH_TOKEN):
        return await call_next(request)

    scope = get_rate_limit_scope(request.method, request.url.path)
    if not scope:
        return await call_next(request)

    allowed, retry_after = consume_rate_limit(scope, get_client_ip(request))
    if allowed:
        return await call_next(request)

    response = JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down and try again shortly."},
    )
    response.headers["Retry-After"] = str(retry_after)
    response.headers["X-Request-ID"] = get_request_id(request.headers)
    return response


def database_ready() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(PUBLIC_INDEX)


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(DASHBOARD_INDEX)


@app.get("/viewer", include_in_schema=False)
def viewer(request: Request):
    response = RedirectResponse(url="/dashboard", status_code=307)
    if VIEWER_ACCESS_TOKEN:
        response.set_cookie(
            key="nasahub_viewer_token",
            value=VIEWER_ACCESS_TOKEN,
            httponly=True,
            secure=is_secure_request(request),
            samesite="lax",
        )
        response.set_cookie(
            key="nasahub_viewer_mode",
            value="1",
            httponly=False,
            secure=is_secure_request(request),
            samesite="lax",
        )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/viewer/logout", include_in_schema=False)
def viewer_logout():
    response = RedirectResponse(url="/dashboard", status_code=307)
    response.delete_cookie(key="nasahub_viewer_token")
    response.delete_cookie(key="nasahub_viewer_mode")
    response.headers["Cache-Control"] = "no-store"
    return response


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
