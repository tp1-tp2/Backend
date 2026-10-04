"""Constant-load variant of locustfile.py for E6 fault injection — inject.py's
docstring asks for "moderate stable load" (50-100 concurrent users) running
alongside the fault, not a ramp. A LoadTestShape subclass (as in locustfile.py)
overrides --users/--spawn-rate, so this reuses the same TranscribeUser via a
shape-free file instead of duplicating the class.

Usage:
    E4_USERS_CSV=users.csv E4_SAMPLE_AUDIO=/path/to/sample.wav \
        locust -f locustfile_constant.py --host http://localhost:8000 \
        --headless --users 50 --spawn-rate 10 --run-time 5m
"""
# E4_MODE=sync|async picks which of the two is active (the other is abstract).
from locustfile import JobUser, TranscribeUser  # noqa: F401
