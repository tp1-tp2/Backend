#!/usr/bin/env python
"""Orchestrates the v2 experiments per architectural dimension
(docs/10-experimentos-v2.md): it switches the stack between configurations
via environment variables + `docker compose up --force-recreate`, waits until
the stack is ready, and runs the measurement scripts.

Phases (run one or several):
  e8  performance  — inference throughput matrix (device x precision x batch)
  e9  adaptation   — load burst vs. the runtime adaptation mechanism (C2.3)
  e4  scalability  — ramp: V1-CPU sync, V2-CPU sync, V2-GPU sync, V2-GPU async
  e6  availability — fault-injection scenarios D1..D7
  e3  performance  — proposed vs. monolith, both on GPU

Examples:
  python run_v2_suite.py --phase e8 --audio clip.wav
  python run_v2_suite.py --phase e9 e6 --audio clip.wav
  python run_v2_suite.py --phase e4 --audio clip.wav --repeats 3 \\
      --steps 10,50,100,200,500,1000 --step-seconds 180
  python run_v2_suite.py --phase e8 --audio clip.wav --quick   # smoke test

Everything is written under experiments/results/ (gitignored).
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = HERE / "results"
PY = sys.executable
# Host URL of the api-gateway (GATEWAY_PORT in docker-compose.yml; 8000 by default)
GW = os.environ.get("GATEWAY_URL", "http://localhost:8000")

BASE_FILES = ["-f", str(ROOT / "docker-compose.yml")]
GPU_FILES = BASE_FILES + ["-f", str(ROOT / "docker-compose.gpu.yml")]

# ---- configurations (docs/10-experimentos-v2.md, "Diseño general") ----
V1_CPU = {
    "AUTH_MODE": "remote", "RESTART_POLICY": "on-failure",
    "FORCE_DEVICE": "cpu", "FORCE_COMPUTE_TYPE": "fp32", "FORCE_BATCH_SIZE": "1",
    "MAX_QUEUE_DEPTH": "100000", "ADMISSION_MAX_WAIT_SECONDS": "100000",
    "JOB_WORKER_ENABLED": "false", "DEVICE": "cpu",
}
V2_CPU = {"FORCE_DEVICE": "cpu", "DEVICE": "cpu"}
V2_GPU: dict = {}

E8_MATRIX = [
    ("cpu-fp32-b1", {"FORCE_DEVICE": "cpu", "FORCE_COMPUTE_TYPE": "fp32", "FORCE_BATCH_SIZE": "1"}),
    ("cpu-int8-b1", {"FORCE_DEVICE": "cpu", "FORCE_COMPUTE_TYPE": "int8", "FORCE_BATCH_SIZE": "1"}),
    ("cuda-fp32-b1", {"FORCE_DEVICE": "cuda", "FORCE_COMPUTE_TYPE": "fp32", "FORCE_BATCH_SIZE": "1"}),
    ("cuda-fp16-b1", {"FORCE_DEVICE": "cuda", "FORCE_COMPUTE_TYPE": "fp16", "FORCE_BATCH_SIZE": "1"}),
    ("cuda-fp16-b4", {"FORCE_DEVICE": "cuda", "FORCE_COMPUTE_TYPE": "fp16", "FORCE_BATCH_SIZE": "4"}),
    ("cuda-fp16-b8", {"FORCE_DEVICE": "cuda", "FORCE_COMPUTE_TYPE": "fp16", "FORCE_BATCH_SIZE": "8"}),
    ("cuda-fp16-b16", {"FORCE_DEVICE": "cuda", "FORCE_COMPUTE_TYPE": "fp16", "FORCE_BATCH_SIZE": "16"}),
]

E9_SCENARIOS = [
    ("A-gpu-adaptive", {"DEVICE": "cuda"}),
    ("B-cpu-adaptive", {"FORCE_DEVICE": "cpu", "DEVICE": "cpu"}),
    ("C-cpu-to-gpu", {"DEVICE": "cpu"}),
]

# (scenario, container, mode, target health, load mode, extra env)
E6_SCENARIOS = [
    ("D1-asr-crash", "backend-asr-service-1", "crash", "http://localhost:8004/health", "sync", {}),
    ("D2-auth-crash-local", "backend-auth-service-1", "crash", "http://localhost:8001/health", "sync", {}),
    ("D2b-auth-crash-remote", "backend-auth-service-1", "crash", "http://localhost:8001/health", "sync",
     {"AUTH_MODE": "remote"}),
    ("D3-trans-crash", "backend-transcription-manager-1", "crash", "http://localhost:8005/health", "sync", {}),
    ("D4-asr-crash-async", "backend-asr-service-1", "crash", "http://localhost:8004/health", "async", {}),
    ("D5-redis-crash", "backend-redis-1", "crash", "docker:backend-redis-1", "sync", {}),
    ("D6-asr-pause", "backend-asr-service-1", "pause", "http://localhost:8004/health", "sync", {}),
]
NEIGHBOURS = [f"{GW}/health", "http://localhost:8001/health",
              "http://localhost:8003/health", "http://localhost:8005/health"]


def log(msg: str) -> None:
    print(f"\n=== [{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def compose(files, env_overrides: dict, *args: str) -> None:
    env = dict(os.environ)
    # Clear every knob first so a previous configuration never leaks in.
    for key in set(V1_CPU) | {"FORCE_COMPUTE_TYPE", "FORCE_BATCH_SIZE", "ADAPTIVE_MODE",
                              "MONOLITH_DEVICE"}:
        env.pop(key, None)
    env.update(env_overrides)
    subprocess.run(["docker", "compose", *files, *args], cwd=ROOT, env=env, check=True)


def wait_ready(urls: list[str], timeout: float = 300.0) -> None:
    deadline = time.time() + timeout
    pending = list(urls)
    while pending and time.time() < deadline:
        pending = [u for u in pending if not _ok(u)]
        if pending:
            time.sleep(2)
    if pending:
        raise RuntimeError(f"Not ready after {timeout}s: {pending}")


def _ok(url: str) -> bool:
    try:
        return httpx.get(url, timeout=3).status_code == 200
    except Exception:
        return False


def apply_config(env: dict, gpu: bool, services: list[str] | None = None) -> None:
    files = GPU_FILES if gpu else BASE_FILES
    compose(files, env, "up", "-d", "--force-recreate", "--no-build", *(services or []))
    wait_ready(["http://localhost:8004/ready"] if services == ["asr-service"]
               else [f"{GW}/health", "http://localhost:8004/ready"])


def run(cmd: list[str], cwd: Path, extra_env: dict | None = None) -> None:
    env = dict(os.environ)
    env.update(extra_env or {})
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=False)


def ensure_users(host: str, out: Path, count: int) -> Path:
    if not out.exists():
        run([PY, "seed_test_users.py", "--base-url", host, "--count", str(count), "--out", str(out)],
            HERE / "e4_load_test")
    return out


# ------------------------------------------------------------------ phases
def phase_e8(a) -> None:
    levels = ["1", "2", "4"] if a.quick else ["1", "2", "4", "8", "16", "32"]
    secs = "15" if a.quick else str(a.e8_seconds)
    src = ["--manifest", a.manifest] if a.manifest else ["--audio", a.audio]
    labels = []
    for label, env in (E8_MATRIX[:1] + E8_MATRIX[5:6] if a.quick else E8_MATRIX):
        log(f"E8 {label}")
        apply_config({**env, "ADAPTIVE_MODE": "false"}, gpu=True, services=["asr-service"])
        run([PY, "bench.py", "--label", label, *src, "--levels", *levels,
             "--seconds-per-level", secs], HERE / "e8_inference_throughput")
        labels.append(str(RESULTS / f"e8_{label}.csv"))
    run([PY, "report.py", "--csv", *labels, "--baseline", "cpu-fp32-b1",
         "--out", str(RESULTS / "e8_report.md")], HERE / "e8_inference_throughput")


def phase_e9(a) -> None:
    burst = ["--idle-s", "10", "--burst-s", "45", "--cooldown-s", "45"] if a.quick else []
    for label, env in E9_SCENARIOS:
        log(f"E9 {label}")
        apply_config({**env, "ADAPTIVE_MODE": "true"}, gpu=True, services=["asr-service"])
        run([PY, "observe.py", "--label", label, "--audio", a.audio, *burst], HERE / "e9_adaptation")


def phase_e4(a) -> None:
    runs = [("S1-v1-cpu-sync", V1_CPU, False, "sync"),
            ("S2-v2-cpu-sync", V2_CPU, False, "sync"),
            ("S3-v2-gpu-sync", V2_GPU, True, "sync"),
            ("S4-v2-gpu-async", V2_GPU, True, "async")]
    for label, env, gpu, mode in runs:
        for rep in range(1, a.repeats + 1):
            tag = f"e4v2_{label}_r{rep}"
            log(f"E4 {tag}")
            apply_config(env, gpu=gpu)
            users = ensure_users(GW, RESULTS / "users_v2_proposed.csv", 30)
            raw = RESULTS / f"{tag}_raw.csv"
            raw.unlink(missing_ok=True)
            run([PY, "-m", "locust", "-f", "locustfile.py", "--host", GW,
                 "--headless", "--only-summary", "--csv", str(RESULTS / tag)],
                HERE / "e4_load_test",
                {"E4_USERS_CSV": str(users), "E4_SAMPLE_AUDIO": a.audio, "E4_MODE": mode,
                 "E4_RAW_CSV": str(raw), "E4_STEPS": a.steps, "E4_STEP_SECONDS": str(a.step_seconds)})
            run([PY, "slo_report.py", "--raw", str(raw), "--step-seconds", str(a.step_seconds),
                 "--audio-seconds", str(a.audio_seconds), "--label", tag,
                 "--out", str(RESULTS / f"{tag}_slo.md")], HERE / "e4_load_test")


def phase_e3(a) -> None:
    for label, host in (("proposed", GW), ("monolith", "http://localhost:8006")):
        for rep in range(1, a.repeats + 1):
            tag = f"e3v2_{label}_r{rep}"
            log(f"E3 {tag}")
            apply_config(V2_GPU, gpu=True)
            users = ensure_users(host, RESULTS / f"users_v2_{label}.csv", 30)
            raw = RESULTS / f"{tag}_raw.csv"
            raw.unlink(missing_ok=True)
            run([PY, "-m", "locust", "-f", "locustfile.py", "--host", host, "--headless",
                 "--only-summary", "--csv", str(RESULTS / tag)], HERE / "e4_load_test",
                {"E4_USERS_CSV": str(users), "E4_SAMPLE_AUDIO": a.audio, "E4_MODE": "sync",
                 "E4_RAW_CSV": str(raw), "E4_STEPS": a.steps, "E4_STEP_SECONDS": str(a.step_seconds)})
            run([PY, "slo_report.py", "--raw", str(raw), "--step-seconds", str(a.step_seconds),
                 "--label", tag, "--out", str(RESULTS / f"{tag}_slo.md")], HERE / "e4_load_test")


def phase_e6(a) -> None:
    duration, fault_at, outage = ("120", "30", "30") if a.quick else ("240", "60", "60")
    for scen, container, mode, target, load_mode, env in E6_SCENARIOS:
        log(f"E6 {scen}")
        apply_config({**V2_GPU, **env}, gpu=True)
        users = ensure_users(GW, RESULTS / "users_v2_proposed.csv", 30)
        run([PY, "run_scenario.py", "--scenario", scen, "--container", container, "--mode", mode,
             "--target-health", target, "--neighbor-health", *[n for n in NEIGHBOURS if n != target],
             "--host", GW, "--users-csv", str(users), "--sample-audio", a.audio, "--load-mode", load_mode,
             "--users", str(a.e6_users), "--duration-s", duration, "--fault-at", fault_at,
             "--outage-s", outage], HERE / "e6_fault_injection")
    # D7: monolith baseline under the same fault
    log("E6 D7-monolith-crash")
    apply_config(V2_GPU, gpu=True)
    users = ensure_users("http://localhost:8006", RESULTS / "users_v2_monolith.csv", 30)
    run([PY, "run_scenario.py", "--scenario", "D7-monolith-crash",
         "--container", "backend-monolith-baseline-1", "--mode", "crash",
         "--target-health", "http://localhost:8006/health", "--host", "http://localhost:8006",
         "--users-csv", str(users), "--sample-audio", a.audio, "--load-mode", "sync",
         "--users", str(a.e6_users), "--duration-s", duration, "--fault-at", fault_at],
        HERE / "e6_fault_injection")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", nargs="+", choices=["e8", "e9", "e4", "e6", "e3"], required=True)
    ap.add_argument("--audio", required=True, help="16 kHz WAV clip used as the load sample")
    ap.add_argument("--audio-seconds", type=float, default=None)
    ap.add_argument("--manifest", default=None, help="E8 only: cycle real clips + WER control")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--steps", default="10,50,100,200,500,1000")
    ap.add_argument("--step-seconds", type=int, default=180)
    ap.add_argument("--e8-seconds", type=int, default=60)
    ap.add_argument("--e6-users", type=int, default=50)
    ap.add_argument("--quick", action="store_true", help="Short smoke-test versions of each phase")
    a = ap.parse_args()
    a.audio = str(Path(a.audio).resolve())
    if a.audio_seconds is None:
        import wave

        with wave.open(a.audio, "rb") as w:
            a.audio_seconds = w.getnframes() / float(w.getframerate())
    RESULTS.mkdir(exist_ok=True)
    for phase in a.phase:
        globals()[f"phase_{phase}"](a)
    log("done — see experiments/results/")


if __name__ == "__main__":
    main()
