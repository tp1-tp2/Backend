# Feature: asr-platform-backend
import json

from hypothesis import given, settings
from hypothesis import strategies as st

from app.schemas.audio import AudioMetadata
from app.services.metadata_service import format_json, parse


_PROBE = st.fixed_dictionaries({
    "format": st.sampled_from(["wav", "mp3", "flac", "ogg"]),
    "duration": st.floats(min_value=0.1, max_value=3600.0, allow_nan=False),
    "sample_rate": st.integers(min_value=8000, max_value=48000),
    "channels": st.integers(min_value=1, max_value=2),
    "bit_rate": st.integers(min_value=8000, max_value=320000),
    "codec": st.one_of(st.none(), st.just("pcm_s16le"), st.just("mp3")),
})


@settings(max_examples=100)
@given(probe=_PROBE)
def test_property_parse_format_roundtrip(probe):
    """Property 1: parse → format_json → parse preserves all fields."""
    original = parse(probe)
    json_str = format_json(original)
    data = json.loads(json_str)

    # Reconstruct using camelCase aliases
    restored = AudioMetadata(
        format=data["format"],
        duration=data["duration"],
        sampleRate=data["sampleRate"],
        bitRate=data["bitRate"],
        channels=data["channels"],
        codec=data.get("codec"),
    )

    assert restored.sample_rate == original.sample_rate
    assert restored.bit_rate == original.bit_rate
    assert restored.channels == original.channels
    assert restored.format == original.format
    assert abs(restored.duration - original.duration) < 1e-6


@settings(max_examples=100)
@given(probe=_PROBE)
def test_property_format_json_has_camel_case_keys(probe):
    """Property 3: format_json always produces camelCase fields with correct types."""
    metadata = parse(probe)
    data = json.loads(format_json(metadata))

    assert "sampleRate" in data
    assert "bitRate" in data
    assert isinstance(data["sampleRate"], int)
    assert isinstance(data["bitRate"], int)
    assert isinstance(data["duration"], float)
    assert isinstance(data["channels"], int)
    assert isinstance(data["format"], str)
