#!/usr/bin/env python
"""E6 v2 — Fault injection, end to end, in one command.

v1 needed two terminals (Locust in one, inject.py in the other), did only a
graceful `docker stop` (which the `on-failure` restart policy ignores, so
recovery was never observed), and the success rate had to be read by hand
from Locust's CSV. This orchestrator:

  1. starts a constant Locust load (sync or async mode) with raw per-request
     logging (locustfile.py's E4_RAW_CSV),
  2. after --fault-at seconds injects ONE fault into ONE container:
       stop  — graceful stop; the script restarts it after --outage-s
               (models a planned/operator outage of fixed length)
       crash — SIGKILL the container's main process from the Docker host's
               PID namespace (a privileged helper container). Docker sees an
               unexpected exit, so the restart policy applies -> measures MTTR.
               This is the realistic "process crashed" fault.
       kill  — `docker kill`. Docker treats it as a MANUAL stop, so the
               restart policy is NOT applied (same pitfall as v1's
               `docker stop`); kept only to reproduce that behaviour
       pause — freeze the process (docker pause) for --outage-s: the
               container is "up" but unresponsive, the nastiest case for
               health checks and timeouts
  3. polls /health of the target and its neighbours every second,
  4. computes, from the raw requests: success rate before / during / after
     the outage, failure-type breakdown, detection time, MTTR, propagation,
     and (async mode) whether any submitted job was LOST.

Usage (from experiments/e6_fault_injection/):
    python run_scenario.py --scenario asr-kill --container backend-asr-service-1 \\
        --mode kill --target-health http://localhost:8004/health \\
        --neighbor-health http://localhost:8000/health http://localhost:8001/health \\
        --users-csv ../e4_load_test/users_local_proposed.csv --sample-audio clip.wav \\
        --load-mode sync --users 50 --duration-s 240 --fault-at 60 --outage-s 60

Outputs ../results/e6v2_<scenario>.{summary.json,md,raw.csv,health.csv}
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pandas as pd

HERE = Path(__file__).resolve().parent
LOAD_DIR = HERE.parent / "e4_load_test"


def _healthy(url: str) -> bool:
    if url.startswith("docker:"):  # container-level health, for non-HTTP targets (redis)
        r = _docker("inspect", "-f", "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}",
                    url.split(":", 1)[1])
        parts = r.stdout.split()
        return bool(parts) and parts[0] == "running" and (len(parts) == 1 or parts[1] == "healthy")
    try:
        return httpx.get(url, timeout=2.0).status_code == 200
    except Exception:
        return False


def _docker(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True)


def _restart_policy(container: str) -> str:
    r = _docker("inspect", "-f", "{{.HostConfig.RestartPolicy.Name}}", container)
    return r.stdout.strip() or "unknown"


class HealthMonitor(threading.Thread):
    def __init__(self, urls: dict[str, str]):
        super().__init__(daemon=True)
        self.urls = urls  # label -> url
        self.samples: list[dict] = []
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            now = time.time()
            for label, url in self.urls.items():
                self.samples.append({"ts": now, "label": label, "healthy": _healthy(url)})
            self._stop.wait(1.0)

    def stop(self):
        self._stop.set()


def _start_load(args, raw_csv: Path) -> subprocess.Popen:
    env = dict(os.environ)
    env.update({
        "E4_USERS_CSV": str(Path(args.users_csv).resolve()),
        "E4_SAMPLE_AUDIO": str(Path(args.sample_audio).resolve()),
        "E4_MODE": args.load_mode,
        "E4_RAW_CSV": str(raw_csv),
        "E4_REQUEST_TIMEOUT_SECONDS": str(args.request_timeout_s),
    })
    cmd = [
        sys.executable, "-m", "locust", "-f", "locustfile_constant.py",
        "--host", args.host, "--headless",
        "--users", str(args.users), "--spawn-rate", str(args.spawn_rate),
        "--run-time", f"{int(args.duration_s)}s", "--only-summary",
    ]
    if args.load_mode == "async":
        # Let users finish the job they are polling instead of being killed
        # mid-poll at run-time end (otherwise in-flight jobs are never scored).
        cmd += ["--stop-timeout", str(int(args.request_timeout_s))]
    return subprocess.Popen(cmd, cwd=LOAD_DIR, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def _first(samples, label, after, healthy):
    for s in samples:
        if s["label"] == label and s["ts"] >= after and s["healthy"] == healthy:
            return s["ts"]
    return None


def _rate(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"requests": 0, "success_rate": None}
    return {"requests": int(len(frame)), "success_rate": round(float(frame["success"].mean()), 4)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--container", required=True)
    ap.add_argument("--mode", choices=["crash", "stop", "kill", "pause"], default="crash")
    ap.add_argument("--target-health", required=True)
    ap.add_argument("--neighbor-health", nargs="*", default=[])
    ap.add_argument("--host", default="http://localhost:8000")
    ap.add_argument("--users-csv", required=True)
    ap.add_argument("--sample-audio", required=True)
    ap.add_argument("--load-mode", choices=["sync", "async"], default="sync")
    ap.add_argument("--users", type=int, default=50)
    ap.add_argument("--spawn-rate", type=float, default=10)
    ap.add_argument("--duration-s", type=float, default=240)
    ap.add_argument("--fault-at", type=float, default=60)
    ap.add_argument("--outage-s", type=float, default=60,
                    help="stop/pause: how long the fault lasts before the script reverts it")
    ap.add_argument("--request-timeout-s", type=float, default=150)
    ap.add_argument("--name", default=None, help="Request name to score (default by load mode)")
    ap.add_argument("--results-dir", default=str(HERE.parent / "results"))
    args = ap.parse_args()

    out_dir = Path(args.results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / f"e6v2_{args.scenario}"
    raw_csv = prefix.with_suffix(".raw.csv")
    raw_csv.unlink(missing_ok=True)

    policy = _restart_policy(args.container)
    health_urls = {"target": args.target_health}
    health_urls.update({f"neighbor:{u}": u for u in args.neighbor_health})
    monitor = HealthMonitor(health_urls)

    print(f"[{args.scenario}] restart policy of {args.container}: {policy}")
    load = _start_load(args, raw_csv)
    monitor.start()
    t_start = time.time()

    time.sleep(args.fault_at)
    t_fault = time.time()
    print(f"[{args.scenario}] injecting {args.mode} into {args.container}")
    if args.mode == "crash":
        pid = _docker("inspect", "-f", "{{.State.Pid}}", args.container).stdout.strip()
        _docker("run", "--rm", "--privileged", "--pid=host", "alpine:3.20", "kill", "-9", pid)
    elif args.mode == "kill":
        _docker("kill", "--signal", "SIGKILL", args.container)
    elif args.mode == "stop":
        _docker("stop", args.container)
    else:
        _docker("pause", args.container)

    t_revert = None
    if args.mode in ("stop", "pause"):
        time.sleep(args.outage_s)
        t_revert = time.time()
        _docker("start" if args.mode == "stop" else "unpause", args.container)
        print(f"[{args.scenario}] reverted fault ({'start' if args.mode == 'stop' else 'unpause'})")

    remaining = args.duration_s - (time.time() - t_start) + 10
    try:
        _, stderr = load.communicate(timeout=max(remaining, 30) + args.request_timeout_s)
    except subprocess.TimeoutExpired:
        load.kill()
        stderr = ""
    monitor.stop()
    monitor.join(timeout=5)

    # Safety net: never leave the stack broken behind us.
    state = _docker("inspect", "-f", "{{.State.Status}}", args.container).stdout.strip()
    if state == "paused":
        _docker("unpause", args.container)
    elif state in ("exited", "created"):
        _docker("start", args.container)

    with open(prefix.with_suffix(".health.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ts", "label", "healthy"])
        w.writeheader()
        w.writerows(monitor.samples)

    detected = _first(monitor.samples, "target", t_fault, healthy=False)
    recovered = _first(monitor.samples, "target", detected or t_fault, healthy=True) if detected else None
    neighbours_degraded = {
        label: any((not s["healthy"]) for s in monitor.samples
                   if s["label"] == label and s["ts"] >= t_fault)
        for label in health_urls if label != "target"
    }

    df = pd.read_csv(raw_csv) if raw_csv.exists() else pd.DataFrame()
    name = args.name or ("/api/v1/transcribe" if args.load_mode == "sync" else "job_e2e")
    summary = {
        "scenario": args.scenario, "container": args.container, "mode": args.mode,
        "restart_policy": policy, "load_mode": args.load_mode, "users": args.users,
        "request_scored": name,
        "detection_time_s": round(detected - t_fault, 2) if detected else None,
        "mttr_s": round(recovered - t_fault, 2) if recovered else None,
        "outage_reverted_by_script_s": round(t_revert - t_fault, 2) if t_revert else None,
        "neighbour_degraded": neighbours_degraded,
    }
    if not df.empty:
        df = df[df["name"] == name].copy()
        df["success"] = df["success"].astype(int).astype(bool)
        # Windows by COMPLETION time (raw ts): a request in flight when the
        # fault hits fails during the outage, so it is counted there — not in
        # "before", which must reflect the healthy baseline.
        df["start_ts"] = df["ts"] - df["response_time_ms"] / 1000.0
        outage_end = recovered or t_revert or (t_fault + args.outage_s)
        before = df[df["ts"] < t_fault]
        during = df[(df["ts"] >= t_fault) & (df["ts"] < outage_end)]
        after = df[df["ts"] >= outage_end]
        summary.update({
            "before": _rate(before), "during": _rate(during), "after": _rate(after),
            "overall": _rate(df),
            "during_failures_by_status": {
                str(k): int(v) for k, v in
                during[~during["success"]].groupby(during["status"].astype(str)).size().items()
            },
        })
        if args.load_mode == "async":
            # job_e2e failures after the fault = submitted jobs that never completed
            # Jobs submitted before the run ended that did not reach "done":
            # failed, timed out, or never scored. 0 = at-least-once held.
            affected = df[df["ts"] >= t_fault]
            summary["jobs_completed_after_fault"] = int(affected["success"].sum())
            summary["jobs_lost"] = int((~affected["success"]).sum())

    prefix.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = [f"# E6 v2 — {args.scenario}", "", "```json", json.dumps(summary, indent=2), "```"]
    if stderr and "Traceback" in stderr:
        md += ["", "Locust stderr (tail):", "```", stderr[-2000:], "```"]
    prefix.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
