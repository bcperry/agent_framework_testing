"""Dev-only stand-in for Microsoft Entra ID token issuance and validation.

The claims here are deliberately shaped like real Entra access tokens (``oid``,
``upn``, ``roles``, ``scp``, ``aud``, ``iss``, ``tid``), so everything downstream
reads exactly what it would read in production.

PRODUCTION SEAM
---------------
Only :func:`decode_token` changes for real Entra:
  * fetch your tenant JWKS (``https://login.microsoftonline.us/{tid}/discovery/v2.0/keys``)
  * verify the RS256 signature against the matching ``kid``
  * validate ``aud`` against your API's Application ID URI and ``iss`` against your tenant

:func:`mint_user_token` disappears entirely -- in production the token is minted by
Entra via the auth code / on-behalf-of flow, never by this app.
"""

import os
import time
import uuid

import jwt

# Dev-only symmetric key. Real Entra tokens are RS256-signed by Microsoft and this
# app would hold no signing key at all. Shared via env so the API and MCP server agree.
_DEV_SIGNING_KEY = os.getenv(
    "DEMO_JWT_SIGNING_KEY", "dev-only-demo-key-not-a-production-secret"
)

ALGORITHM = "HS256"
AUDIENCE = "api://records-demo"
TENANT_ID = "00000000-0000-0000-0000-000000000000"
ISSUER = f"https://sts.windows.net/{TENANT_ID}/"

TOKEN_LIFETIME_SECONDS = 3600


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired, or fails validation."""


def mint_user_token(user: dict) -> str:
    """Issue a dev token for a demo user. Stands in for the Entra auth code flow."""
    now = int(time.time())
    payload = {
        "aud": AUDIENCE,
        "iss": ISSUER,
        "tid": TENANT_ID,
        "iat": now,
        "nbf": now,
        "exp": now + TOKEN_LIFETIME_SECONDS,
        "jti": str(uuid.uuid4()),
        "sub": user["oid"],
        "oid": user["oid"],
        "upn": user["upn"],
        "name": user["name"],
        "roles": user["roles"],
        "scp": user["scp"],
    }
    return jwt.encode(payload, _DEV_SIGNING_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Validate a token and return its claims.

    Signature, expiry, audience and issuer are all enforced -- an unverified decode
    would defeat the entire point of the demo.
    """
    try:
        return jwt.decode(
            token,
            _DEV_SIGNING_KEY,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "aud", "iss", "oid"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"Token failed validation: {exc}") from exc


def bearer_from_header(authorization: str | None) -> dict:
    """Extract and validate claims from an ``Authorization: Bearer <token>`` header."""
    if not authorization:
        raise TokenError("Missing Authorization header.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise TokenError("Authorization header must use the Bearer scheme.")
    return decode_token(token)
