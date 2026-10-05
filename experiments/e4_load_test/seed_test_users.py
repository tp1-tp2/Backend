#!/usr/bin/env python
"""Registers N test users and writes their credentials to a CSV — Locust
round-robins through these so concurrent logins aren't all hitting the same
account (more representative of real concurrent load).

Usage:
    python seed_test_users.py --base-url http://127.0.0.1:8000 --count 50 --out users.csv
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.asr_client import register, unique_test_email  # noqa: E402

PASSWORD = "ExperimentPass123!"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--out", default="users.csv")
    args = parser.parse_args()

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["email", "password"])
        for i in range(args.count):
            email = unique_test_email("e4")
            register(args.base_url, email, PASSWORD, f"Load Test User {i}")
            writer.writerow([email, PASSWORD])
            print(f"[{i + 1}/{args.count}] registered {email}")

    print(f"\n{args.count} users written to {args.out}")


if __name__ == "__main__":
    main()
