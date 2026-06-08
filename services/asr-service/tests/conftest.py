import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, settings

from app.main import app

settings.register_profile("ci", max_examples=100, deadline=5000, suppress_health_check=[HealthCheck.too_slow])
settings.load_profile("ci")


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
