import hashlib
import hmac
from datetime import timedelta
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from .models import now

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY_HASH = hasher.hash("unusable-random-dummy-password")


def verify_password(encoded, password):
    try:
        return hasher.verify(encoded or DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        return False


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def keyed_digest(key, value):
    return hmac.new(key.encode(), value.encode(), hashlib.sha256).hexdigest()


def token(settings, subject, kind, **extra):
    t = now()
    return jwt.encode({"sub": subject, "kind": kind, "iat": t, "exp": t + timedelta(minutes=settings.token_minutes),
                       "iss": "labaccess", "aud": "labaccess", **extra},
                      settings.signing_key.get_secret_value(), algorithm="HS256")


def decode(settings, value):
    return jwt.decode(value, settings.signing_key.get_secret_value(), algorithms=["HS256"],
                      issuer="labaccess", audience="labaccess", options={"require": ["exp", "iat", "sub", "kind"]})
