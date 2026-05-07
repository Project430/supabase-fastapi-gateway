"""Bearer-token helpers.

The gateway never validates the JWT signature itself: it forwards the user's
Supabase access token to Supabase, which is the source of truth. We only:

  * confirm the header looks like `Bearer <token>`
  * decode the unsigned payload to extract the user id (`sub`) when a route
    needs it for query scoping

If you need cryptographic verification at the gateway (for example, to reject
expired tokens before any upstream call), wire in `python-jose` and verify
against Supabase's JWKS. That is outside the scope of this template.
"""

import base64
import binascii
import json

from fastapi import Header, HTTPException, status


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer <token>.",
        )

    return token.strip()


def get_optional_bearer_token(
    authorization: str | None = Header(default=None),
) -> str | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer <token>.",
        )

    return token.strip()


def _decode_token_payload(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format.",
        )

    body = parts[1]
    padding = "=" * (-len(body) % 4)

    try:
        decoded = base64.urlsafe_b64decode(body + padding)
        payload = json.loads(decoded)
    except (binascii.Error, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )
    return payload


def get_user_id_from_token(token: str) -> str:
    payload = _decode_token_payload(token)
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a subject.",
        )
    return sub
