"""E4 — Scalability under increasing load.

Real HTTP against a live deployment (per the protocol: "no ASGI in-memory —
debe ser HTTP real contra el despliegue"), not the in-process TestClient every
existing test in services/api-gateway/tests/e2e/ uses.

Usage:
    # 1. Seed test users once:
    python seed_test_users.py --base-url http://localhost:8000 --count 50 --out users.csv

    # 2. Run the ramp (10->50->100->200->500->1000, ~3min/step by default):
    E4_USERS_CSV=users.csv E4_SAMPLE_AUDIO=/path/to/sample.wav \
        locust -f locustfile.py --host http://localhost:8000 --headless \
        --csv ../results/e4_run --html ../results/e4_run.html

Point --host at the monolith-baseline's URL (http://localhost:8006) to run the
same ramp against E3's control architecture — same shape, different target.
"""
import csv
import itertools
import os
from pathlib import Path

from locust import HttpUser, LoadTestShape, between, task

_USERS_CSV = os.environ.get("E4_USERS_CSV", "users.csv")
_SAMPLE_AUDIO = os.environ.get("E4_SAMPLE_AUDIO", "sample.wav")


def _load_credentials() -> list[tuple[str, str]]:
    path = Path(_USERS_CSV)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run seed_test_users.py first (see this file's docstring)"
        )
    with open(path, newline="", encoding="utf-8") as f:
        return [(row["email"], row["password"]) for row in csv.DictReader(f)]


_credentials_cycle = itertools.cycle(_load_credentials())


class TranscribeUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        email, password = next(_credentials_cycle)
        resp = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        resp.raise_for_status()
        self.token = resp.json()["token"]

    @task
    def transcribe(self):
        with open(_SAMPLE_AUDIO, "rb") as f:
            self.client.post(
                "/api/v1/transcribe",
                headers={"Authorization": f"Bearer {self.token}"},
                files={"file": (Path(_SAMPLE_AUDIO).name, f, "application/octet-stream")},
                name="/api/v1/transcribe",
            )


class RampUpShape(LoadTestShape):
    """10 -> 50 -> 100 -> 200 -> 500 -> 1000 concurrent users, holding each
    step long enough to stabilize (E4: "2-5 min por escalón").
    """

    step_users = [10, 50, 100, 200, 500, 1000]
    step_duration_s = int(os.environ.get("E4_STEP_DURATION_S", 180))
    spawn_rate = 10

    def tick(self):
        run_time = self.get_run_time()
        step_index = int(run_time // self.step_duration_s)
        if step_index >= len(self.step_users):
            return None
        return (self.step_users[step_index], self.spawn_rate)
