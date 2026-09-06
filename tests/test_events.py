"""
Event endpoint tests.

MongoDB is mocked via monkeypatch so tests run without a real DB.
Each test patches get_events_collection() to return an in-memory
dict-based fake that mirrors the pymongo/motor API we actually use.
"""
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId


# ── Fake collection ───────────────────────────────────────────────────────────

def _make_fake_collection(initial_docs: list | None = None):
    """
    Returns a fake async Motor collection with find, find_one,
    insert_one, update_one, delete_one.
    """
    store: dict[str, dict] = {}

    if initial_docs:
        for doc in initial_docs:
            store[str(doc["_id"])] = doc

    # Cursor-like object for find()
    class FakeCursor:
        def __init__(self, docs):
            self._docs = docs

        def sort(self, *args, **kwargs):
            return self

        async def to_list(self, length=None):
            return list(self._docs.values())

    col = MagicMock()
    col.find.return_value = FakeCursor(store)
    col.find_one = AsyncMock(side_effect=lambda q: _find_one(store, q))
    col.insert_one = AsyncMock(side_effect=lambda doc: _insert(store, doc))
    col.update_one = AsyncMock(side_effect=lambda q, upd: _update(store, q, upd))
    col.delete_one = AsyncMock(side_effect=lambda q: _delete(store, q))
    return col, store


def _find_one(store, query):
    oid = query.get("_id")
    if oid is None:
        return None
    return store.get(str(oid))


def _insert(store, doc):
    oid = ObjectId()
    doc["_id"] = oid
    store[str(oid)] = doc
    result = MagicMock()
    result.inserted_id = oid
    return result


def _update(store, query, update):
    oid = query.get("_id")
    if oid and str(oid) in store:
        store[str(oid)].update(update.get("$set", {}))


def _delete(store, query):
    oid = query.get("_id")
    if oid:
        store.pop(str(oid), None)


# ── Fixtures ──────────────────────────────────────────────────────────────────

FUTURE_DATE = str(date.today() + timedelta(days=7))
PAST_DATE   = str(date.today() - timedelta(days=1))

VALID_PAYLOAD = {
    "title":       "Tech Fest 2025",
    "description": "Annual technology showcase at the main campus",
    "date":        FUTURE_DATE,
    "time":        "10:00",
    "venue":       "Main Auditorium",
    "category":    "Technical",
}


# ── List events ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_events_empty(client, monkeypatch):
    col, _ = _make_fake_collection([])
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.get("/api/events")
    assert resp.status_code == 200
    assert resp.json() == []


# ── Create event ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_event_valid(client, monkeypatch):
    col, store = _make_fake_collection()
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.post("/api/events", json=VALID_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Tech Fest 2025"
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_create_event_missing_title(client, monkeypatch):
    col, _ = _make_fake_collection()
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "title"}
    resp = await client.post("/api/events", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_event_empty_title(client, monkeypatch):
    col, _ = _make_fake_collection()
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.post("/api/events", json={**VALID_PAYLOAD, "title": "   "})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_event_past_date(client, monkeypatch):
    col, _ = _make_fake_collection()
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.post("/api/events", json={**VALID_PAYLOAD, "date": PAST_DATE})
    assert resp.status_code == 422
    assert "future" in resp.text.lower()


@pytest.mark.asyncio
async def test_create_event_invalid_date_format(client, monkeypatch):
    col, _ = _make_fake_collection()
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.post("/api/events", json={**VALID_PAYLOAD, "date": "not-a-date"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_event_invalid_time_format(client, monkeypatch):
    col, _ = _make_fake_collection()
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.post("/api/events", json={**VALID_PAYLOAD, "time": "10am"})
    assert resp.status_code == 422


# ── Get single event ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_event_valid_id(client, monkeypatch):
    from datetime import datetime, timezone
    oid = ObjectId()
    doc = {
        "_id": oid, **VALID_PAYLOAD,
        "max_attendees": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    col, _ = _make_fake_collection([doc])
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.get(f"/api/events/{oid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Tech Fest 2025"


@pytest.mark.asyncio
async def test_get_event_not_found(client, monkeypatch):
    col, _ = _make_fake_collection([])
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    fake_id = str(ObjectId())
    resp = await client.get(f"/api/events/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_event_malformed_id(client, monkeypatch):
    col, _ = _make_fake_collection([])
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.get("/api/events/not-an-id")
    assert resp.status_code == 422


# ── Update event ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_event_title(client, monkeypatch):
    from datetime import datetime, timezone
    oid = ObjectId()
    doc = {
        "_id": oid, **VALID_PAYLOAD,
        "max_attendees": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    col, _ = _make_fake_collection([doc])
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.put(f"/api/events/{oid}", json={"title": "Updated Title"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_update_event_not_found(client, monkeypatch):
    col, _ = _make_fake_collection([])
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.put(f"/api/events/{ObjectId()}", json={"title": "x"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_event_no_fields(client, monkeypatch):
    col, _ = _make_fake_collection([])
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.put(f"/api/events/{ObjectId()}", json={})
    assert resp.status_code == 422


# ── Delete event ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_event_valid(client, monkeypatch):
    from datetime import datetime, timezone
    oid = ObjectId()
    doc = {
        "_id": oid, **VALID_PAYLOAD,
        "max_attendees": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    col, _ = _make_fake_collection([doc])
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.delete(f"/api/events/{oid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(oid)


@pytest.mark.asyncio
async def test_delete_event_not_found(client, monkeypatch):
    col, _ = _make_fake_collection([])
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)
    resp = await client.delete(f"/api/events/{ObjectId()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_event_twice(client, monkeypatch):
    """Second delete must return 404, not 500."""
    from datetime import datetime, timezone
    oid = ObjectId()
    doc = {
        "_id": oid, **VALID_PAYLOAD,
        "max_attendees": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    col, store = _make_fake_collection([doc])
    monkeypatch.setattr("app.routes.events.get_events_collection", lambda: col)

    resp1 = await client.delete(f"/api/events/{oid}")
    assert resp1.status_code == 200

    # Remove from store to simulate it being gone
    store.pop(str(oid), None)

    resp2 = await client.delete(f"/api/events/{oid}")
    assert resp2.status_code == 404
