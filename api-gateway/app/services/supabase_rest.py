"""Thin client for Supabase's PostgREST endpoint (`/rest/v1/<table>`).

The gateway forwards the user's bearer token, so PostgREST applies the same
Row Level Security policies it would if the browser called Supabase directly.
"""

from typing import Any

import httpx

from app.config import Settings


class UpstreamRestError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def call_supabase_rest(
    *,
    settings: Settings,
    method: str,
    table: str,
    token: str,
    query_params: dict[str, str] | None = None,
    json_body: Any = None,
    prefer: str | None = None,
) -> Any:
    headers: dict[str, str] = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {token}",
    }
    if prefer:
        headers["Prefer"] = prefer
    if json_body is not None:
        headers["Content-Type"] = "application/json"

    timeout = httpx.Timeout(30.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method.upper(),
                settings.rest_url(table),
                headers=headers,
                params=query_params,
                json=json_body,
            )
    except httpx.RequestError as exc:
        raise UpstreamRestError(
            status_code=502,
            detail="Failed to reach the data service.",
        ) from exc

    if response.status_code == 204 or not response.content:
        if response.is_error:
            raise UpstreamRestError(
                status_code=response.status_code,
                detail="Database operation failed.",
            )
        return None

    try:
        payload = response.json()
    except ValueError as exc:
        if not response.is_error:
            return None
        raise UpstreamRestError(
            status_code=502,
            detail="Database returned a non-JSON response.",
        ) from exc

    if response.is_error:
        raise UpstreamRestError(
            status_code=response.status_code,
            detail="Database operation failed.",
        )

    return payload
