import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_health_does_not_depend_on_db(client, monkeypatch):
    """
    /health must return 200 even if DB is down.
    Liveness probe should NEVER check the database.
    """
    from app import database
    monkeypatch.setattr(database, "ping_db", lambda: False)

    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_version_shape(client):
    resp = await client.get("/version")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("version", "build", "hostname", "environment", "uptime_seconds"):
        assert key in body, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_load_runs_and_returns(client):
    """Short duration so tests don't hang."""
    resp = await client.get("/load?duration=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["duration"] == 2
    assert body["cores_used"] >= 1


@pytest.mark.asyncio
async def test_load_duration_capped(client):
    """Duration > 120 should be rejected with 422."""
    resp = await client.get("/load?duration=9999")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_load_duration_zero_rejected(client):
    resp = await client.get("/load?duration=0")
    assert resp.status_code == 422
