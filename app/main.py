import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import ping_db
from app.routes.devops import router as devops_router
from app.routes.events import router as events_router
from app.routes.frontend import router as frontend_router
from config import APP_VERSION, BUILD_NUMBER, ENVIRONMENT

# ── Logging — JSON to stdout (required for container log collection) ───────────

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)


# ── Lifespan — runs on startup and shutdown ───────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting eventapp {APP_VERSION} build {BUILD_NUMBER} [{ENVIRONMENT}]")
    db_ok = await ping_db()
    if db_ok:
        logger.info("MongoDB connection: OK")
    else:
        logger.warning("MongoDB connection: FAILED — /ready will return 503")
    yield
    # Shutdown
    logger.info("Shutting down eventapp")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Campus Events API",
    description="Event management backend with DevOps utility endpoints",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 1)
    logger.info(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} duration={duration_ms}ms"
    )
    return response


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(devops_router)   # /health /ready /version /load
app.include_router(events_router)   # /api/events CRUD
app.include_router(frontend_router) # Frontend routes


# ── Static files (frontend) ───────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="app/static"), name="static")
