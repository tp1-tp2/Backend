from unittest.mock import AsyncMock, MagicMock, patch

from app.services import job_queue


def _fake(groups, undelivered):
    client = MagicMock()
    client.xgroup_create = AsyncMock()
    client.xinfo_groups = AsyncMock(return_value=groups)
    client.xrange = AsyncMock(return_value=undelivered)
    return client


async def test_backlog_ignores_stale_lag_and_counts_undelivered():
    """XINFO's lag said 1197 on a fully consumed stream (E4 v2); the backlog
    must come from the real undelivered range + pending."""
    groups = [{"name": "asr-workers", "pending": 2, "lag": 1197, "last-delivered-id": "10-0"}]
    client = _fake(groups, [("11-0", {}), ("12-0", {})])
    with patch.object(job_queue, "_client", return_value=client):
        assert await job_queue.backlog() == 4
    kwargs = client.xrange.await_args.kwargs
    assert kwargs["min"] == "(10-0" and kwargs["max"] == "+"


async def test_backlog_zero_when_consumed_even_if_lag_is_stale():
    groups = [{b"name": b"asr-workers", b"pending": 0, b"lag": 1197, b"last-delivered-id": b"99-0"}]
    with patch.object(job_queue, "_client", return_value=_fake(groups, [])):
        assert await job_queue.backlog() == 0
