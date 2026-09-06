import pytest

@pytest.mark.asyncio
async def test_frontend_index(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Overview" in resp.text

@pytest.mark.asyncio
async def test_frontend_events(client):
    resp = await client.get("/events")
    assert resp.status_code == 200
    assert "Events" in resp.text

@pytest.mark.asyncio
async def test_frontend_about(client):
    resp = await client.get("/about")
    assert resp.status_code == 200
    assert "About the Project" in resp.text
    assert "Shubham Kr Singh" in resp.text
    assert "Sinchana V" in resp.text
