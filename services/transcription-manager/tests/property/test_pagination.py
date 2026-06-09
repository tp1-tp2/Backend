from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.exceptions import InvalidPageSizeError
from app.services.transcription_service import TranscriptionService


def _make_service() -> TranscriptionService:
    svc = TranscriptionService(MagicMock())
    svc._trans = AsyncMock()
    svc._words = AsyncMock()
    svc._trans.get_by_user.return_value = []
    svc._trans.count_by_user.return_value = 0
    return svc


@settings(max_examples=100)
@given(page_size=st.integers(min_value=1, max_value=100))
def test_property_valid_page_size_never_raises(page_size):
    """Any page_size in [1, 100] must be accepted without validation error."""
    import asyncio
    svc = _make_service()
    # Should not raise
    asyncio.run(svc.list_by_user("uid-1", page=1, page_size=page_size))


@settings(max_examples=100)
@given(page_size=st.one_of(
    st.integers(max_value=0),
    st.integers(min_value=101),
))
def test_property_invalid_page_size_always_raises(page_size):
    """Any page_size outside [1, 100] must raise InvalidPageSizeError."""
    import asyncio
    svc = _make_service()
    with pytest.raises(InvalidPageSizeError):
        asyncio.run(svc.list_by_user("uid-1", page=1, page_size=page_size))
