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
# CPU-only host (docs/14-optimizacion-cpu.md): v2 + CTranslate2 engine with
# parallel lanes. Lanes/precision are set by --lanes/--compute-type (from E8).
V2_CPU_CT2 = {"FORCE_DEVICE": "cpu", "DEVICE": "cpu", "ENGINE": "ctranslate2"}
V1_CPU["ENGINE"] = "transformers"
CPU_ONLY = False

# E8 on a CPU-only host: engine x precision x lanes (batch is always 1 on CPU).
E8_CPU_MATRIX = [
    ("cpu-fp32-b1", {"FORCE_DEVICE": "cpu", "FORCE_COMPUTE_TYPE": "fp32", "FORCE_BATCH_SIZE": "1",
                     "ENGINE": "transformers"}),
    ("cpu-int8-b1", {"FORCE_DEVICE": "cpu", "FORCE_COMPUTE_TYPE": "int8", "FORCE_BATCH_SIZE": "1",
                     "ENGINE": "transformers"}),
] + [
    # (lanes x threads per lane) on the 6-core/12-thread evaluation CPU
    (f"ct2-{ct}-l{n}t{t}", {"FORCE_DEVICE": "cpu", "FORCE_COMPUTE_TYPE": ct, "FORCE_BATCH_SIZE": "1",
                            "ENGINE": "ctranslate2", "INFERENCE_LANES": str(n), "CT2_CPU_THREADS": str(t)})
    for ct, n, t in [("fp32", 1, 6), ("fp32", 3, 2), ("int8", 1, 6), ("int8", 2, 3), ("int8", 3, 2),
                     ("int8", 6, 1), ("int8", 2, 6), ("int8", 3, 4), ("int8", 4, 3)]
]

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
MONOLITH_HEALTH = "http://localhost:8006/health"
NEIGHBOURS = [f"{GW}/health", "http://localhost:8001/health",
              "http://localhost:8003/health", "http://localhost:8005/health"]


def log(msg: str) -> None:
    print(f"\n=== [{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def compose(files, env_overrides: dict, *args: str) -> None:
    env = dict(os.environ)
    # Clear every knob first so a previous configuration never leaks in.
    for key in set(V1_CPU) | {"FORCE_COMPUTE_TYPE", "FORCE_BATCH_SIZE", "ADAPTIVE_MODE",
                              "MONOLITH_DEVICE", "ENGINE", "INFERENCE_LANES", "CT2_CPU_THREADS",
                              "MONOLITH_ENGINE", "MONOLITH_COMPUTE_TYPE", "MONOLITH_LANES",
                              "MONOLITH_CT2_CPU_THREADS"}:
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
    files = GPU_FILES if (gpu and not CPU_ONLY) else BASE_FILES
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
def v2_env(a) -> dict:
    """The full v2 configuration for this host."""
    if not CPU_ONLY:
        return V2_GPU
    env = {**V2_CPU_CT2, "INFERENCE_LANES": str(a.lanes), "CT2_CPU_THREADS": str(a.threads)}
    if a.compute_type:
        env["FORCE_COMPUTE_TYPE"] = a.compute_type
    return env


def e3_env(a) -> dict:
    env = dict(v2_env(a))
    if CPU_ONLY:
        # Same engine, precision and lanes in both architectures: E3 isolates
        # the architectural style, not the inference engine.
        ct = a.compute_type or "fp32"
        env.update({"MONOLITH_ENGINE": "ctranslate2", "MONOLITH_LANES": str(a.lanes),
                    "MONOLITH_CT2_CPU_THREADS": str(a.threads),
                    "MONOLITH_COMPUTE_TYPE": ct, "FORCE_COMPUTE_TYPE": ct})
    return env


def phase_e8(a) -> None:
    levels = ["1", "2", "4"] if a.quick else ["1", "2", "4", "8", "16", "32"]
    secs = "15" if a.quick else str(a.e8_seconds)
    src = ["--manifest", a.manifest] if a.manifest else ["--audio", a.audio]
    labels = []
    matrix = E8_CPU_MATRIX if CPU_ONLY else (E8_MATRIX[:1] + E8_MATRIX[5:6] if a.quick else E8_MATRIX)
    if a.e8_only:
        matrix = [m for m in matrix if m[0] in a.e8_only]
    if CPU_ONLY and not a.quick:
        levels = ["1", "2", "4", "8", "16"]
    for label, env in matrix:
        log(f"E8 {label}")
        apply_config({**env, "ADAPTIVE_MODE": "false"}, gpu=True, services=["asr-service"])
        run([PY, "bench.py", "--label", label, *src, "--levels", *levels,
             "--seconds-per-level", secs], HERE / "e8_inference_throughput")
        labels.append(str(RESULTS / f"e8_{label}.csv"))
    run([PY, "report.py", "--csv", *labels, "--baseline", "cpu-fp32-b1",
         "--out", str(RESULTS / "e8_report.md")], HERE / "e8_inference_throughput")


def phase_e9(a) -> None:
    burst = ["--idle-s", "10", "--burst-s", "45", "--cooldown-s", "45"] if a.quick else []
    scenarios = E9_SCENARIOS
    if CPU_ONLY:
        scenarios = [("B-cpu-adaptive-ct2", v2_env(a)),
                     ("B-cpu-adaptive-transformers", {"FORCE_DEVICE": "cpu", "DEVICE": "cpu",
                                                      "ENGINE": "transformers"})]
    for label, env in scenarios:
        for rep in range(1, a.repeats + 1):
            tag = label if a.repeats == 1 else f"{label}_r{rep}"
            log(f"E9 {tag}")
            apply_config({**env, "ADAPTIVE_MODE": "true"}, gpu=True, services=["asr-service"])
            run([PY, "observe.py", "--label", tag, "--audio", a.audio, *burst], HERE / "e9_adaptation")


def phase_e4(a) -> None:
    runs = [("S1-v1-cpu-sync", V1_CPU, False, "sync"),
            ("S2-v2-cpu-sync", V2_CPU, False, "sync"),
            ("S3-v2-gpu-sync", V2_GPU, True, "sync"),
            ("S4-v2-gpu-async", V2_GPU, True, "async")]
    if CPU_ONLY:
        runs = [("S1-v1-cpu-sync", V1_CPU, False, "sync"),
                ("S2-v2-cpu-sync", v2_env(a), False, "sync"),
                ("S2b-v2-cpu-async", v2_env(a), False, "async")]
    if a.e4_only:
        runs = [r for r in runs if r[0] in a.e4_only]
    for label, env, gpu, mode in runs:
        for rep in range(1, a.repeats + 1):
            tag = f"e4v2_{label}_r{rep}"
            log(f"E4 {tag}")
            apply_config(env, gpu=gpu)
            users = ensure_users(GW, RESULTS / "users_v2_proposed.csv", 30)
            raw = RESULTS / f"{tag}_raw.csv"
            raw.unlink(missing_ok=True)
            # async: let users finish polling jobs already accepted when the ramp ends
            stop = ["--stop-timeout", "1800"] if mode == "async" else []
            run([PY, "-m", "locust", "-f", "locustfile.py", "--host", GW,
                 "--headless", "--only-summary", "--csv", str(RESULTS / tag), *stop],
                HERE / "e4_load_test",
                {"E4_USERS_CSV": str(users), "E4_SAMPLE_AUDIO": a.audio, "E4_MODE": mode,
                 "E4_RAW_CSV": str(raw), "E4_STEPS": a.steps, "E4_STEP_SECONDS": str(a.step_seconds),
                 # clients wait as long as the backlog needs; completion is also
                 # verified server-side below (C2.2), independent of client patience
                 "E4_JOB_TIMEOUT_SECONDS": "3600"})
            if mode == "async":
                job_completion(raw, RESULTS / f"{tag}_jobs.json")
            run([PY, "slo_report.py", "--raw", str(raw), "--step-seconds", str(a.step_seconds),
                 "--audio-seconds", str(a.audio_seconds), "--label", tag,
                 "--out", str(RESULTS / f"{tag}_slo.md")], HERE / "e4_load_test")


def _redis_backlog() -> int | None:
    """lag + pending of the job consumer group (same definition as
    audio-processor's job_queue.backlog)."""
    out = subprocess.run(["docker", "exec", "backend-redis-1", "redis-cli", "XINFO", "GROUPS", "asr:jobs"],
                         capture_output=True, text=True).stdout.splitlines()
    try:  # key/value lines; nil values come back as empty lines, so keep them
        vals = dict(zip(out[::2], out[1::2]))
        if not vals.get("lag"):  # lag unknown: fall back to "anything pending/undelivered"
            return int(vals.get("pending") or 0)
        return int(vals["lag"]) + int(vals.get("pending") or 0)
    except ValueError:
        return None


def job_completion(raw: Path, out: Path, timeout_s: float = 1800.0) -> None:
    """C2.2 (async): after the ramp, wait for the queue to drain and compare
    jobs ACCEPTED (202 at the gateway, from the raw CSV) with jobs the worker
    PROCESSED / FAILED (asr-service counters, reset at each run's recreate)."""
    import csv
    import json

    t0 = time.time()
    backlog = _redis_backlog()
    while (backlog is None or backlog > 0) and time.time() - t0 < timeout_s:
        time.sleep(5)
        backlog = _redis_backlog()
    drain_s = time.time() - t0
    accepted = submitted = 0
    with open(raw, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("name") == "/api/v1/jobs":
                submitted += 1
                accepted += str(row.get("status")) == "202"
    worker = {}
    try:
        worker = httpx.get("http://localhost:8004/status/scheduler", timeout=10).json().get("job_worker", {})
    except Exception as exc:
        worker = {"error": str(exc)}
    result = {
        "submitted": submitted, "accepted": accepted,
        "acceptance_rate": accepted / submitted if submitted else None,
        "processed": worker.get("processed"), "failed": worker.get("failed"),
        "duplicates": worker.get("duplicates"), "reclaimed": worker.get("reclaimed"),
        "completion_rate": (worker.get("processed") or 0) / accepted if accepted else None,
        "backlog_after_drain": backlog, "drain_seconds_after_locust": round(drain_s, 1),
    }
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("job completion:", result, flush=True)


def phase_e3(a) -> None:
    for label, host in (("proposed", GW), ("monolith", "http://localhost:8006")):
        for rep in range(1, a.repeats + 1):
            tag = f"e3v2_{label}_r{rep}"
            log(f"E3 {tag}")
            apply_config(e3_env(a), gpu=True)
            wait_ready([MONOLITH_HEALTH])  # both architectures up before any load
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
    scenarios = E6_SCENARIOS
    if a.e6_only:
        scenarios = [x for x in scenarios if x[0] in a.e6_only]
    for scen, container, mode, target, load_mode, env in scenarios:
        for rep in range(1, a.repeats + 1):
            tag = scen if a.repeats == 1 else f"{scen}_r{rep}"
            log(f"E6 {tag}")
            apply_config({**v2_env(a), **env}, gpu=True)
            users = ensure_users(GW, RESULTS / "users_v2_proposed.csv", 30)
            run([PY, "run_scenario.py", "--scenario", tag, "--container", container, "--mode", mode,
                 "--target-health", target, "--neighbor-health", *[n for n in NEIGHBOURS if n != target],
                 "--host", GW, "--users-csv", str(users), "--sample-audio", a.audio,
                 "--load-mode", load_mode, "--users", str(a.e6_users), "--duration-s", duration,
                 "--fault-at", fault_at, "--outage-s", outage], HERE / "e6_fault_injection")
    if a.e6_only and "D7-monolith-crash" not in a.e6_only:
        return
    # D7: monolith baseline under the same fault (same engine as the proposal)
    for rep in range(1, a.repeats + 1):
        tag = "D7-monolith-crash" if a.repeats == 1 else f"D7-monolith-crash_r{rep}"
        log(f"E6 {tag}")
        apply_config(e3_env(a), gpu=True)
        wait_ready([MONOLITH_HEALTH])  # the monolith starts slower than the gateway
        users = ensure_users("http://localhost:8006", RESULTS / "users_v2_monolith.csv", 30)
        run([PY, "run_scenario.py", "--scenario", tag,
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
    ap.add_argument("--cpu-only", action="store_true",
                    help="Host without an NVIDIA GPU: CPU matrix/scenarios (docs/14-optimizacion-cpu.md)")
    ap.add_argument("--lanes", type=int, default=3, help="--cpu-only: inference lanes for v2")
    ap.add_argument("--threads", type=int, default=2, help="--cpu-only: CTranslate2 threads per lane")
    ap.add_argument("--compute-type", default=None, help="--cpu-only: pin v2 precision (fp32|int8)")
    ap.add_argument("--e8-only", nargs="*", default=None, help="Subset of E8 labels")
    ap.add_argument("--e4-only", nargs="*", default=None, help="Subset of E4 run labels")
    ap.add_argument("--e6-only", nargs="*", default=None, help="Subset of E6 scenarios")
    a = ap.parse_args()
    global CPU_ONLY
    CPU_ONLY = a.cpu_only
    a.audio = str(Path(a.audio).resolve())
    if a.manifest:
        a.manifest = str(Path(a.manifest).resolve())
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
