# Feature: asr-platform-backend, Task 1.4: Docker health check unit tests
import pytest
from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_structure(client: TestClient):
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "api-gateway"
    assert "version" in data
    assert "timestamp" in data
    assert "checks" in data


def test_health_content_type(client: TestClient):
    response = client.get("/health")
    assert "application/json" in response.headers["content-type"]
