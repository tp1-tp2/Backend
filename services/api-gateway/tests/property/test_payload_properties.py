# Feature: asr-platform-backend
from typing import Optional

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel, EmailStr, Field, ValidationError


class RegistrationRequest(BaseModel):
    """Mirrors user-service RegistrationRequest contract validated at the gateway boundary."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)


# ---------- Hypothesis strategies ----------

_valid_email = st.emails()

_valid_password = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="!@#$%^&*"),
    min_size=8,
    max_size=128,
)

_valid_full_name = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs")),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip())


# ---------- Property 2: RegistrationRequest round-trip (Req 26.4) ----------

@settings(max_examples=100)
@given(
    email=_valid_email,
    password=_valid_password,
    full_name=_valid_full_name,
)
def test_property_registration_request_roundtrip(email, password, full_name):
    """Property 2: Valid RegistrationRequest survives serialize → parse with fields preserved."""
    original = RegistrationRequest(email=email, password=password, full_name=full_name)
    data = original.model_dump()
    restored = RegistrationRequest.model_validate(data)

    assert str(restored.email) == str(original.email)
    assert restored.password == original.password
    assert restored.full_name == original.full_name


# ---------- Property 4: Invalid payloads always raise ValidationError (Req 26.2) ----------

_short_password = st.text(max_size=7)
_long_password = st.text(min_size=129, max_size=200)
_empty_name = st.just("")
_long_name = st.text(min_size=101, max_size=200)
_invalid_email = st.one_of(
    st.just("not-an-email"),
    st.just("@nodomain"),
    st.just("missing@"),
    st.just(""),
    st.just("spaces in@email.com"),
)


@settings(max_examples=100)
@given(
    email=_valid_email,
    password=st.one_of(_short_password, _long_password),
    full_name=_valid_full_name,
)
def test_property_invalid_password_raises_validation_error(email, password, full_name):
    """Property 4a: Passwords outside [8, 128] chars always raise ValidationError."""
    with pytest.raises(ValidationError):
        RegistrationRequest(email=email, password=password, full_name=full_name)


@settings(max_examples=100)
@given(
    email=_valid_email,
    password=_valid_password,
    full_name=st.one_of(_empty_name, _long_name),
)
def test_property_invalid_full_name_raises_validation_error(email, password, full_name):
    """Property 4b: full_name empty or >100 chars always raises ValidationError."""
    with pytest.raises(ValidationError):
        RegistrationRequest(email=email, password=password, full_name=full_name)


@settings(max_examples=100)
@given(
    email=_invalid_email,
    password=_valid_password,
    full_name=_valid_full_name,
)
def test_property_invalid_email_raises_validation_error(email, password, full_name):
    """Property 4c: Malformed email addresses always raise ValidationError."""
    with pytest.raises(ValidationError):
        RegistrationRequest(email=email, password=password, full_name=full_name)


@settings(max_examples=100)
@given(
    missing_field=st.sampled_from(["email", "password", "full_name"]),
    email=_valid_email,
    password=_valid_password,
    full_name=_valid_full_name,
)
def test_property_missing_required_field_raises_validation_error(
    missing_field, email, password, full_name
):
    """Property 4d: Omitting any required field always raises ValidationError."""
    payload = {"email": email, "password": password, "full_name": full_name}
    del payload[missing_field]
    with pytest.raises(ValidationError):
        RegistrationRequest.model_validate(payload)
