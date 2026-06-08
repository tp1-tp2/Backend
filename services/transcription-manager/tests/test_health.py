# Feature: asr-platform-backend, Task 1.4: Docker health check unit tests
def test_health_returns_200(client):
    assert client.get("/health").status_code == 200


def test_health_response_structure(client):
    data = client.get("/health").json()
    assert data["status"] == "healthy"
    assert data["service"] == "transcription-manager"
    assert "timestamp" in data and "checks" in data


def test_health_content_type(client):
    assert "application/json" in client.get("/health").headers["content-type"]
