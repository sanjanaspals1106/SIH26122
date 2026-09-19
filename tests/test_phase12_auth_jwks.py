import base64
import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

import backend.shared.auth as auth_mod
from backend.shared.auth import decode_supabase_jwt, get_jwks_client


@pytest.fixture(autouse=True)
def reset_auth_jwks_cache():
    """Ensure each test gets a clean JWKS client instance and isolated environment."""
    auth_mod._jwks_client = None
    auth_mod._jwks_url = None
    yield
    auth_mod._jwks_client = None
    auth_mod._jwks_url = None


@pytest.fixture
def es256_keys():
    """Generate two separate ES256 keypairs for signing and verification testing."""
    priv_key_1 = ec.generate_private_key(ec.SECP256R1())
    pub_key_1 = priv_key_1.public_key()

    priv_key_2 = ec.generate_private_key(ec.SECP256R1())
    pub_key_2 = priv_key_2.public_key()

    def get_jwk(pub_key, kid):
        numbers = pub_key.public_numbers()

        def b64url(val: int) -> str:
            raw = val.to_bytes((val.bit_length() + 7) // 8, byteorder="big")
            return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

        return {
            "kty": "EC",
            "crv": "P-256",
            "x": b64url(numbers.x),
            "y": b64url(numbers.y),
            "kid": kid,
            "use": "sig",
            "alg": "ES256",
        }

    jwks_dict = {
        "keys": [
            get_jwk(pub_key_1, "key-valid-1"),
            get_jwk(pub_key_2, "key-valid-2"),
        ]
    }

    return {
        "priv_1": priv_key_1,
        "pub_1": pub_key_1,
        "priv_2": priv_key_2,
        "pub_2": pub_key_2,
        "jwks": jwks_dict,
    }


def test_es256_jwks_valid_token(monkeypatch, es256_keys):
    """A valid ES256 token signed with a key published in JWKS is verified successfully."""
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    token = jwt.encode(
        {"sub": "user-uuid-123", "email": "engineer@example.com"},
        es256_keys["priv_1"],
        algorithm="ES256",
        headers={"kid": "key-valid-1"},
    )

    client = get_jwks_client("https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    client.fetch_data = lambda: es256_keys["jwks"]

    payload = decode_supabase_jwt(token)
    assert payload["sub"] == "user-uuid-123"
    assert payload["email"] == "engineer@example.com"


def test_es256_jwks_key_selection_by_kid(monkeypatch, es256_keys):
    """Verification selects the correct key from a multi-key JWKS based on header kid."""
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    # Token signed by key 2
    token = jwt.encode(
        {"sub": "user-uuid-key2", "role": "authenticated"},
        es256_keys["priv_2"],
        algorithm="ES256",
        headers={"kid": "key-valid-2"},
    )

    client = get_jwks_client("https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    client.fetch_data = lambda: es256_keys["jwks"]

    payload = decode_supabase_jwt(token)
    assert payload["sub"] == "user-uuid-key2"


def test_es256_jwks_invalid_signature_rejected(monkeypatch, es256_keys):
    """A token signed with an untrusted private key fails signature verification with 401."""
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    # Forged keypair not matching key-valid-1 in JWKS
    rogue_priv = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(
        {"sub": "attacker-id"},
        rogue_priv,
        algorithm="ES256",
        headers={"kid": "key-valid-1"},
    )

    client = get_jwks_client("https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    client.fetch_data = lambda: es256_keys["jwks"]

    with pytest.raises(HTTPException) as exc_info:
        decode_supabase_jwt(token)
    assert exc_info.value.status_code == 401
    assert "Signature verification failed" in str(exc_info.value.detail)


def test_unsupported_algorithm_rejected(monkeypatch, es256_keys):
    """An HS256 or 'none' token presented against an ES256 JWKS endpoint is strictly rejected with 401."""
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    # Attempt algorithm confusion attack with HS256 using a 32-byte secret
    secret = "a" * 32
    token = jwt.encode(
        {"sub": "attacker-id"},
        secret,
        algorithm="HS256",
        headers={"kid": "key-valid-1"},
    )

    client = get_jwks_client("https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    client.fetch_data = lambda: es256_keys["jwks"]

    with pytest.raises(HTTPException) as exc_info:
        decode_supabase_jwt(token)
    assert exc_info.value.status_code == 401
    assert "The specified alg value is not allowed" in str(exc_info.value.detail)


def test_unknown_kid_rejected(monkeypatch, es256_keys):
    """A token specifying a kid not present in the JWKS is rejected with 401."""
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    token = jwt.encode(
        {"sub": "user-uuid"},
        es256_keys["priv_1"],
        algorithm="ES256",
        headers={"kid": "non-existent-kid"},
    )

    client = get_jwks_client("https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    client.fetch_data = lambda: es256_keys["jwks"]

    with pytest.raises(HTTPException) as exc_info:
        decode_supabase_jwt(token)
    assert exc_info.value.status_code == 401
    assert "Unable to find a signing key that matches" in str(exc_info.value.detail)


def test_missing_sub_claim_rejected(monkeypatch, es256_keys):
    """A verified token that lacks a 'sub' claim raises HTTP 401."""
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    # Valid signature, but no sub claim
    token = jwt.encode(
        {"email": "nobody@example.com"},
        es256_keys["priv_1"],
        algorithm="ES256",
        headers={"kid": "key-valid-1"},
    )

    client = get_jwks_client("https://mock.supabase.co/auth/v1/.well-known/jwks.json")
    client.fetch_data = lambda: es256_keys["jwks"]

    with pytest.raises(HTTPException) as exc_info:
        decode_supabase_jwt(token)
    assert exc_info.value.status_code == 401
    assert "missing subject claim ('sub')" in str(exc_info.value.detail)


def test_malformed_and_empty_tokens_rejected(monkeypatch, es256_keys):
    """Malformed, non-JWT, and empty tokens are immediately rejected with 401."""
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://mock.supabase.co/auth/v1/.well-known/jwks.json")

    for bad_token in ["", "   ", "not-a-jwt", "part1.part2", "invalid.token.payload"]:
        with pytest.raises(HTTPException) as exc_info:
            decode_supabase_jwt(bad_token)
        assert exc_info.value.status_code == 401


def test_legacy_hs256_secret_verification(monkeypatch):
    """Backward compatibility: If SUPABASE_JWT_SECRET is set to an HMAC secret, HS256 is verified."""
    secret = "a" * 32
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)

    valid_token = jwt.encode({"sub": "legacy-user-1"}, secret, algorithm="HS256")
    payload = decode_supabase_jwt(valid_token)
    assert payload["sub"] == "legacy-user-1"

    # Bad signature
    tampered_token = jwt.encode({"sub": "legacy-user-1"}, "b" * 32, algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        decode_supabase_jwt(tampered_token)
    assert exc_info.value.status_code == 401


def test_http_verification_fallback_on_jwks_connection_error(monkeypatch):
    """When JWKS has a connection error, direct HTTP verification against /auth/v1/user succeeds."""
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://unreachable.jwks.invalid/jwks.json")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://fallback.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_test_key")

    client = get_jwks_client("https://unreachable.jwks.invalid/jwks.json")

    def mock_fetch_fail():
        raise jwt.PyJWKClientConnectionError("Connection timed out")

    client.fetch_data = mock_fetch_fail

    import httpx

    def mock_get(url, headers=None, timeout=None):
        class MockResponse:
            status_code = 200

            def json(self):
                return {"id": "http-user-id", "email": "http@test.internal", "role": "authenticated"}

        assert "https://fallback.supabase.co/auth/v1/user" in url
        assert headers.get("apikey") == "sb_publishable_test_key"
        assert headers.get("Authorization") == f"Bearer {token}"
        return MockResponse()

    monkeypatch.setattr(httpx, "get", mock_get)

    # Valid JWT structure so PyJWKClient attempts get_signing_key_from_jwt before fetch_data raises connection error
    token = jwt.encode({"sub": "will-fail-jwks"}, "secret32byteslong012345678901234", algorithm="HS256", headers={"kid": "k1"})
    payload = decode_supabase_jwt(token)
    assert payload["sub"] == "http-user-id"
    assert payload["email"] == "http@test.internal"
