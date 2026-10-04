"""E4 — Scalability under increasing load (v2).

Real HTTP against a live deployment (per the protocol: "no ASGI in-memory —
debe ser HTTP real contra el despliegue"), not the in-process TestClient every
existing test in services/api-gateway/tests/e2e/ uses.

v2 changes (docs/10-experimentos-v2.md):

1. Success is VALIDATED, not inferred from the status code. v1 counted any
   200 as a success, but audio-processor used to answer 200 with
   `transcription_id: null` when asr-service failed — those now count as
   failures ("no transcription in body"). Every failure is labelled with its
   status class (401/429/503/504/...) so shed load (fast 503) is
   distinguishable from slow failures (504) and auth errors (401).

2. Two load modes, selected with E4_MODE:
   - sync  (default): POST /api/v1/transcribe and wait (E3/E4 v1 comparable).
   - async: POST /api/v1/jobs (202) then poll GET /api/v1/jobs/{id} until
     done/failed. The end-to-end job time is reported as a synthetic request
     named "job_e2e" so it lands in the same stats as the sync path.

3. Every request is also appended to a raw CSV (E4_RAW_CSV) with its
   timestamp, latency, outcome and the user count at that moment, so
   slo_report.py computes EXACT per-step percentiles (Locust's history CSV
   only has 10 s sliding-window percentiles).

4. The ramp is configurable: E4_STEPS (default 10,50,100,200,500,1000) and
   E4_STEP_SECONDS (default 180). Think time: E4_WAIT_MIN/E4_WAIT_MAX (1-3 s).

Usage:
    python seed_test_users.py --base-url http://localhost:8000 --count 50 --out users.csv
    E4_USERS_CSV=users.csv E4_SAMPLE_AUDIO=/path/to/sample.wav E4_MODE=async \\
    E4_RAW_CSV=../results/e4_async_raw.csv \\
        python -m locust -f locustfile.py --host http://localhost:8000 --headless \\
        --csv ../results/e4_async --html ../results/e4_async.html

Point --host at the monolith-baseline's URL (http://localhost:8006) to run the
same ramp against E3's control architecture (sync mode only — the monolith
has no /jobs endpoint by design).
"""
import atexit
import csv
import itertools
import os
import threading
import time
from pathlib import Path

from locust import HttpUser, LoadTestShape, between, events, task

_USERS_CSV = os.environ.get("E4_USERS_CSV", "users.csv")
_SAMPLE_AUDIO = os.environ.get("E4_SAMPLE_AUDIO", "sample.wav")
_MODE = os.environ.get("E4_MODE", "sync").lower()
_RAW_CSV = os.environ.get("E4_RAW_CSV", "")
_WAIT_MIN = float(os.environ.get("E4_WAIT_MIN", "1"))
_WAIT_MAX = float(os.environ.get("E4_WAIT_MAX", "3"))
_JOB_POLL_S = float(os.environ.get("E4_JOB_POLL_SECONDS", "1.0"))
_JOB_TIMEOUT_S = float(os.environ.get("E4_JOB_TIMEOUT_SECONDS", "600"))
_REQUEST_TIMEOUT_S = float(os.environ.get("E4_REQUEST_TIMEOUT_SECONDS", "300"))


def _load_credentials() -> list[tuple[str, str]]:
    path = Path(_USERS_CSV)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run seed_test_users.py first (see this file's docstring)"
        )
    with open(path, newline="", encoding="utf-8") as f:
        return [(row["email"], row["password"]) for row in csv.DictReader(f)]


_credentials_cycle = itertools.cycle(_load_credentials())
_AUDIO_BYTES = Path(_SAMPLE_AUDIO).read_bytes() if Path(_SAMPLE_AUDIO).exists() else None


# ---------------------------------------------------------------- raw logging
class _RawLog:
    FIELDS = ["ts", "name", "response_time_ms", "success", "status", "error", "users"]

    def __init__(self, path: str) -> None:
        self._path = path
        self._rows: list[list] = []
        self._lock = threading.Lock()
        self._header_written = False
        self.runner = None

    def add(self, name, response_time, success, status, error) -> None:
        if not self._path:
            return
        users = self.runner.user_count if self.runner is not None else ""
        with self._lock:
            self._rows.append(
                [round(time.time(), 3), name, round(response_time or 0.0, 1),
                 int(success), status, (error or "")[:120], users]
            )
            if len(self._rows) >= 500:
                self._flush_locked()

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        if not self._path or not self._rows:
            return
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        new_file = not Path(self._path).exists()
        with open(self._path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file and not self._header_written:
                w.writerow(self.FIELDS)
            w.writerows(self._rows)
        self._header_written = True
        self._rows.clear()


RAW = _RawLog(_RAW_CSV)
atexit.register(RAW.flush)


@events.init.add_listener
def _on_init(environment, **_kwargs):
    RAW.runner = environment.runner


@events.request.add_listener
def _on_request(request_type, name, response_time, response_length, response=None,
                exception=None, **_kwargs):
    status = getattr(response, "status_code", "") if response is not None else ""
    RAW.add(name, response_time, exception is None, status, str(exception) if exception else "")


@events.test_stop.add_listener
def _on_stop(**_kwargs):
    RAW.flush()


def _status_label(status) -> str:
    return f"HTTP {status}" if status else "connection error"


# ---------------------------------------------------------------- users
class _AuthedUser(HttpUser):
    abstract = True
    wait_time = between(_WAIT_MIN, _WAIT_MAX)

    def on_start(self):
        email, password = next(_credentials_cycle)
        resp = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        resp.raise_for_status()
        self.token = resp.json()["token"]

    def _files(self):
        return {"file": (Path(_SAMPLE_AUDIO).name, _AUDIO_BYTES, "application/octet-stream")}


class TranscribeUser(_AuthedUser):
    """Synchronous path: the client holds the connection until the text is back."""

    @task
    def transcribe(self):
        with self.client.post(
            "/api/v1/transcribe",
            headers={"Authorization": f"Bearer {self.token}"},
            files=self._files(),
            name="/api/v1/transcribe",
            timeout=_REQUEST_TIMEOUT_S,
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(_status_label(resp.status_code))
                return
            try:
                body = resp.json()
            except ValueError:
                resp.failure("invalid JSON body")
                return
            # Real stack: transcription_id; monolith: transcription_id too.
            if not body.get("transcription_id"):
                resp.failure("no transcription in body")
                return
            resp.success()


class JobUser(_AuthedUser):
    """Asynchronous path: submit (202), then poll until the job finishes."""

    @task
    def submit_and_wait(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        t0 = time.perf_counter()
        with self.client.post(
            "/api/v1/jobs", headers=headers, files=self._files(),
            name="/api/v1/jobs", timeout=60, catch_response=True,
        ) as resp:
            if resp.status_code != 202:
                resp.failure(_status_label(resp.status_code))
                self._fire_e2e(t0, f"submit {_status_label(resp.status_code)}")
                return
            job_id = resp.json().get("job_id")
            resp.success()

        deadline = time.perf_counter() + _JOB_TIMEOUT_S
        while time.perf_counter() < deadline:
            time.sleep(_JOB_POLL_S)
            with self.client.get(
                f"/api/v1/jobs/{job_id}", headers=headers,
                name="/api/v1/jobs/[id]", catch_response=True,
            ) as poll:
                if poll.status_code != 200:
                    poll.failure(_status_label(poll.status_code))
                    continue  # transient (e.g. gateway restarting): keep polling
                poll.success()
                status = poll.json().get("status")
            if status == "done":
                self._fire_e2e(t0, None)
                return
            if status == "failed":
                self._fire_e2e(t0, "job failed")
                return
        self._fire_e2e(t0, "job timeout")

    def _fire_e2e(self, t0: float, error) -> None:
        self.environment.events.request.fire(
            request_type="JOB",
            name="job_e2e",
            response_time=(time.perf_counter() - t0) * 1000.0,
            response_length=0,
            response=None,
            context={},
            exception=Exception(error) if error else None,
        )


# Pick the user class for this run (Locust ignores abstract classes).
TranscribeUser.abstract = _MODE != "sync"
JobUser.abstract = _MODE != "async"


class StepLoadShape(LoadTestShape):
    """Stepped ramp (protocol default: 10->50->100->200->500->1000, 180 s each).
    Override with E4_STEPS / E4_STEP_SECONDS / E4_SPAWN_RATE."""

    targets = [int(x) for x in os.environ.get("E4_STEPS", "10,50,100,200,500,1000").split(",")]
    step_seconds = float(os.environ.get("E4_STEP_SECONDS", os.environ.get("E4_STEP_DURATION_S", "180")))
    spawn_rate = float(os.environ.get("E4_SPAWN_RATE", "10"))

    def tick(self):
        run_time = self.get_run_time()
        step = int(run_time // self.step_seconds)
        if step >= len(self.targets):
            return None
        return self.targets[step], self.spawn_rate
