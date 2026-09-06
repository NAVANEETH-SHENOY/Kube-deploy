import time
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import MONGO_URL, MONGO_DB_NAME

logger = logging.getLogger(__name__)

# Module-level client — reused across requests (Motor is thread/async safe)
_client: AsyncIOMotorClient | None = None
_connected: bool = False
_start_time: float = time.time()


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            MONGO_URL,
            serverSelectionTimeoutMS=3000,  # fail fast on connection check
        )
    return _client


def get_db():
    return get_client()[MONGO_DB_NAME]


def get_events_collection():
    return get_db()["events"]


async def ping_db() -> bool:
    """
    Returns True if MongoDB is reachable.
    Used by /ready endpoint — Kubernetes readiness probe.
    """
    global _connected
    try:
        client = await get_client().admin.command("ping")
        _connected = True
        logger.info(f"MongoDB ping failed: {client}")
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        _connected = False
        logger.warning(f"MongoDB ping failed: {e}")
        return False


def get_uptime() -> float:
    return round(time.time() - _start_time, 1)
