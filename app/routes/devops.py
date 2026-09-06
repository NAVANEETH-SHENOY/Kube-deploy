import logging
import math
import multiprocessing
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.database import get_uptime, ping_db
from app.models import HealthResponse, LoadResponse, ReadyResponse, VersionResponse
from config import APP_VERSION, BUILD_NUMBER, ENVIRONMENT, HOSTNAME

logger = logging.getLogger(__name__)
router = APIRouter(tags=["devops"])

# Maximum allowed /load duration — cap to prevent runaway processes
MAX_LOAD_DURATION = 120


# ── /health ───────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe — is the process alive?",
)
async def health():
    """
    Kubernetes liveness probe.
    Always returns 200 as long as the process is running.
    Does NOT check the database — that is /ready.

    If this returns non-200, K8s restarts the pod.
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc),
    )


# ── /ready ────────────────────────────────────────────────────────────────────

@router.get(
    "/ready",
    summary="Readiness probe — is the app ready to serve traffic?",
)
async def ready():
    """
    Kubernetes readiness probe.
    Returns 200 only if MongoDB is reachable.
    Returns 503 if DB connection fails.

    If this returns non-200, K8s stops sending traffic to this pod
    (but does NOT restart it). Pod stays up, just taken out of rotation.
    """
    db_ok = await ping_db()

    if db_ok:
        return ReadyResponse(ready=True)

    return JSONResponse(
        status_code=503,
        content=ReadyResponse(ready=False, reason="MongoDB unreachable").model_dump(),
    )


# ── /version ──────────────────────────────────────────────────────────────────

@router.get(
    "/version",
    response_model=VersionResponse,
    summary="App version and build info — deployment proof",
)
async def version():
    """
    Returns version info sourced from environment variables set by Jenkins.

    APP_VERSION   — set in deployment.yaml, change v1→v2 for demo
    BUILD_NUMBER  — Jenkins ${BUILD_NUMBER}, increments each pipeline run
    HOSTNAME      — Kubernetes pod name, changes as pods scale
    """
    return VersionResponse(
        version=APP_VERSION,
        build=BUILD_NUMBER,
        hostname=HOSTNAME,
        environment=ENVIRONMENT,
        uptime_seconds=get_uptime(),
    )


# ── /load ─────────────────────────────────────────────────────────────────────

def _cpu_burn(seconds: int) -> None:
    """
    Worker function — runs in a separate process.
    Burns CPU with a tight math loop.
    multiprocessing bypasses Python's GIL so each process uses a full core,
    which is what cgroups / metrics-server measures for HPA.
    """
    end = time.time() + seconds
    while time.time() < end:
        math.sqrt(12345678 ** 2)


@router.get(
    "/load",
    response_model=LoadResponse,
    summary="Artificial CPU load — triggers Kubernetes HPA scaling",
)
async def load(
    duration: int = Query(
        default=30,
        ge=1,
        le=MAX_LOAD_DURATION,
        description="How many seconds to burn CPU (1–120)",
    )
):
    """
    Spawns one process per CPU core and burns CPU for `duration` seconds.

    Use this during the demo:
      1. Run: kubectl get hpa -w
      2. Hit GET /load?duration=60
      3. Watch replicas increase as CPU crosses 50%
      4. After load ends, replicas scale back down (~3–5 min cooldown)

    Duration is capped at 120 seconds to prevent runaway processes.
    """
    cores = multiprocessing.cpu_count()
    logger.info(f"Starting CPU load: {duration}s across {cores} cores")

    procs = [
        multiprocessing.Process(target=_cpu_burn, args=(duration,))
        for _ in range(cores)
    ]

    for p in procs:
        p.start()
    for p in procs:
        p.join()

    logger.info(f"CPU load complete: {duration}s")
    return LoadResponse(
        status="done",
        duration=duration,
        cores_used=cores,
    )
