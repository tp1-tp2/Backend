"""One minimal real-HTTP smoke test against a live stack (docker-compose or
Azure) — register -> login -> hit /health. Bridges the "zero real-HTTP tests"
gap identified while planning experiments/ (every e2e test under
services/api-gateway/tests/e2e/ is fully mocked/in-process) WITHOUT turning
this repo's fast test suite into the experiment harness — that's what
experiments/ is for.

Skipped by default (network + a running stack are not available in normal CI
runs). Opt in with:

    RUN_REAL_STACK_TESTS=1 pytest tests/integration/test_real_stack_smoke.py -v

Point BASE_URL at the monolith-baseline (http://localhost:8006) to smoke-test
that architecture instead of the default microservices stack.
"""
import os
import uuid

import httpx
import pytest

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_REAL_STACK_TESTS") != "1",
    reason="Set RUN_REAL_STACK_TESTS=1 and have a real stack running to opt in",
)


def test_health_ok():
    resp = httpx.get(f"{BASE_URL}/health", timeout=10)
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_register_login_roundtrip():
    email = f"smoke-{uuid.uuid4().hex[:12]}@example.com"  # example.com (RFC 2606); .local is rejected by pydantic[email]
    password = "SmokeTestPass123!"

    register_resp = httpx.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Smoke Test"},
        timeout=30,
    )
    assert register_resp.status_code in (200, 201), register_resp.text

    login_resp = httpx.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert login_resp.status_code == 200, login_resp.text
    assert "token" in login_resp.json()
