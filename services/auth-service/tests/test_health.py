# Feature: asr-platform-backend, Task 1.4: Docker health check unit tests
def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_structure(client):
    data = client.get("/health").json()
    assert data["status"] == "healthy"
    assert data["service"] == "auth-service"
    assert "version" in data
    assert "timestamp" in data
    assert "checks" in data


def test_health_content_type(client):
    response = client.get("/health")
    assert "application/json" in response.headers["content-type"]
