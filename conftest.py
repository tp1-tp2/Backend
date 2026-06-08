import pytest
from hypothesis import settings, HealthCheck

settings.register_profile(
    "ci",
    max_examples=100,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "dev",
    max_examples=20,
    deadline=2000,
)
settings.load_profile("ci")
