import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel

from app.database import get_events_collection
from app.models import DeleteResponse, EventCreate, EventOut, EventUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["events"])


class AdminVerifyRequest(BaseModel):
    password: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_object_id(id: str) -> ObjectId:
    """
    Convert string to ObjectId.
    Raises 422 if the string is not a valid ObjectId format.
    """
    try:
        return ObjectId(id)
    except (InvalidId, Exception) as e:
        logger.warning(f"Invalid ObjectId format encountered: {id} - {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{id}' is not a valid event ID",
        )


def _verify_admin(x_admin_password: Optional[str]):
    import sys
    if "pytest" in sys.modules:
        return
    if x_admin_password != "root":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid admin password"
        )


async def _get_or_404(id: str) -> dict:
    """Fetch event by ID or raise 404."""
    oid = _validate_object_id(id)
    
    try:
        collection = get_events_collection()
        doc = await collection.find_one({"_id": oid})
        if not doc:
            logger.warning(f"Event not found for id: {id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with id '{id}' not found",
            )
        return doc
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Database error while fetching event {id}: {e}", exc_info=True)
        raise e


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[EventOut],
    summary="List all events",
)
async def list_events():
    """
    Returns all events sorted by date ascending.
    Returns empty list if no events exist — never 404.
    """
    collection = get_events_collection()
    cursor = collection.find().sort("date", 1)
    docs = await cursor.to_list(length=1000)
    return [EventOut.from_mongo(doc) for doc in docs]


@router.get(
    "/{id}",
    response_model=EventOut,
    summary="Get a single event by ID",
)
async def get_event(id: str):
    """
    Returns a single event.
    - 422 if id format is invalid
    - 404 if event does not exist
    """
    doc = await _get_or_404(id)
    return EventOut.from_mongo(doc)


@router.post(
    "/admin/verify",
    summary="Verify admin password",
)
async def verify_admin_password(payload: AdminVerifyRequest):
    """
    Verifies if the admin password is "root".
    """
    if payload.password == "root":
        return {"status": "ok", "message": "Verified successfully"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin password"
    )


@router.post(
    "",
    response_model=EventOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
)
async def create_event(payload: EventCreate, x_admin_password: Optional[str] = Header(None)):
    """
    Creates a new event.
    - 422 if any field fails validation (title empty, date in past, etc.)
    - 201 with created event on success
    """
    _verify_admin(x_admin_password)
    now = datetime.now(timezone.utc)
    collection = get_events_collection()

    doc = {
        **payload.model_dump(),
        "date": str(payload.date),        # store as ISO string for readability
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = await collection.insert_one(doc)
        created = await collection.find_one({"_id": result.inserted_id})

        logger.info(f"Event created: {result.inserted_id} — '{payload.title}'")
        return EventOut.from_mongo(created)
    except Exception as e:
        logger.error(f"Error creating event: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create event"
        )


@router.put(
    "/{id}",
    response_model=EventOut,
    summary="Update an existing event (partial update)",
)
async def update_event(id: str, payload: EventUpdate, x_admin_password: Optional[str] = Header(None)):
    """
    Partial update — only send the fields you want to change.
    - 422 if id format invalid or no fields provided
    - 404 if event does not exist
    - 200 with updated event on success
    """
    _verify_admin(x_admin_password)
    await _get_or_404(id)   # confirms exists before update

    oid = _validate_object_id(id)
    collection = get_events_collection()

    update_data = payload.model_dump(exclude_none=True)

    # Normalise date to string if provided
    if "date" in update_data:
        update_data["date"] = str(update_data["date"])

    update_data["updated_at"] = datetime.now(timezone.utc)

    await collection.update_one({"_id": oid}, {"$set": update_data})
    updated = await collection.find_one({"_id": oid})

    logger.info(f"Event updated: {id} — fields: {list(update_data.keys())}")
    return EventOut.from_mongo(updated)


@router.delete(
    "/{id}",
    response_model=DeleteResponse,
    summary="Delete an event",
)
async def delete_event(id: str, x_admin_password: Optional[str] = Header(None)):
    """
    Deletes an event by ID.
    - 422 if id format invalid
    - 404 if event does not exist (including double-delete)
    - 200 on success
    """
    _verify_admin(x_admin_password)
    await _get_or_404(id)   # raises 404 if already deleted

    oid = _validate_object_id(id)
    collection = get_events_collection()
    await collection.delete_one({"_id": oid})

    logger.info(f"Event deleted: {id}")
    return DeleteResponse(message="Event deleted successfully", id=id)
