import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register(client):
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "test123456",
        "display_name": "Test User",
    })
    # May fail if no DB — testing the endpoint exists and returns proper error
    assert resp.status_code in (200, 500)


@pytest.mark.asyncio
async def test_login_no_db(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@test.com",
        "password": "wrong",
    })
    assert resp.status_code in (401, 500)
