"""Hits the real local SQL Server via the real app - no mocks, same convention used
throughout PropertyManager (every test file hits the actual DB)."""
from fastapi.testclient import TestClient


def test_health_check_returns_ok_and_verifies_db_connection(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "database": "connected"}
