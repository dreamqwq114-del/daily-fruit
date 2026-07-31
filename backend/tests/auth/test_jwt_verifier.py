from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.jwt_verifier import JwtVerifier
from app.config import Settings
from app.errors import AuthenticationError, AuthenticationUnavailableError


ISSUER = "https://example.supabase.co/auth/v1"
AUDIENCE = "authenticated"


@dataclass
class SigningKey:
    key: object


class StaticSigningKeyClient:
    def __init__(self, public_key: object) -> None:
        self.public_key = public_key

    def get_signing_key_from_jwt(self, _token: str) -> SigningKey:
        return SigningKey(self.public_key)


@pytest.fixture(scope="module")
def key_pair() -> tuple[object, object]:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key, private_key.public_key()


def settings() -> Settings:
    return Settings(
        _env_file=None,
        APP_ENV="test",
        DEBUG=False,
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_JWT_AUDIENCE=AUDIENCE,
    )


def token_claims(**overrides: object) -> dict[str, object]:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "aud": AUDIENCE,
        "exp": now + timedelta(minutes=10),
        "iat": now,
        "iss": ISSUER,
        "role": "authenticated",
        "session_id": str(uuid4()),
        "sub": str(uuid4()),
    }
    claims.update(overrides)
    return claims


def encode(private_key: object, claims: dict[str, object]) -> str:
    return jwt.encode(claims, private_key, algorithm="RS256")


def verifier(public_key: object) -> JwtVerifier:
    return JwtVerifier(
        settings(),
        signing_key_client=StaticSigningKeyClient(public_key),
    )


def test_valid_token_returns_stable_principal(key_pair) -> None:
    private_key, public_key = key_pair
    claims = token_claims()

    principal = verifier(public_key).verify(encode(private_key, claims))

    assert principal.auth_user_id == UUID(str(claims["sub"]))
    assert principal.session_id == UUID(str(claims["session_id"]))


@pytest.mark.parametrize(
    "claim_overrides",
    [
        {"aud": "wrong"},
        {"iss": "https://attacker.example/auth/v1"},
        {"role": "anon"},
        {"is_anonymous": True},
        {"exp": datetime.now(UTC) - timedelta(seconds=1)},
        {"sub": "not-a-uuid"},
        {"session_id": "not-a-uuid"},
    ],
)
def test_invalid_claims_are_rejected(key_pair, claim_overrides) -> None:
    private_key, public_key = key_pair
    token = encode(private_key, token_claims(**claim_overrides))

    with pytest.raises(AuthenticationError):
        verifier(public_key).verify(token)


def test_symmetric_algorithm_is_rejected(key_pair) -> None:
    _, public_key = key_pair
    token = jwt.encode(token_claims(), "x" * 32, algorithm="HS256")

    with pytest.raises(AuthenticationError):
        verifier(public_key).verify(token)


def test_missing_supabase_config_fails_closed() -> None:
    with pytest.raises(AuthenticationUnavailableError):
        JwtVerifier(Settings(_env_file=None, APP_ENV="test", DEBUG=False))
