"""Thin Edge Function client."""

from typing import Any

import httpx

from app.config import Settings


class UpstreamFunctionError(Exception):
    def __init__(
        self, status_code: int, detail: str, payload: Any | None = None
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.payload = payload


async def invoke_supabase_function(
    *,
    settings: Settings,
    function_name: str,
    token: str | None,
    payload: Any,
    method: str = "POST",
    query_params: dict[str, str] | None = None,
) -> Any:
    headers: dict[str, str] = {
        "apikey": settings.supabase_anon_key,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method.upper() != "GET":
        headers["Content-Type"] = "application/json"

    timeout = httpx.Timeout(60.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            request_kwargs: dict[str, Any] = {
                "headers": headers,
                "params": query_params,
            }
            if method.upper() != "GET" and payload is not None:
                request_kwargs["json"] = payload

            response = await client.request(
                method.upper(),
                settings.function_url(function_name),
                **request_kwargs,
            )
    except httpx.RequestError as exc:
        raise UpstreamFunctionError(
            status_code=502,
            detail="Failed to reach Supabase Edge Function.",
        ) from exc

    try:
        response_payload = response.json()
    except ValueError as exc:
        if not response.is_error:
            return {"content": response.text}
        raise UpstreamFunctionError(
            status_code=502,
            detail="Supabase Edge Function returned a non-JSON response.",
        ) from exc

    if response.is_error:
        detail = "Supabase Edge Function returned an error."
        if isinstance(response_payload, dict):
            detail = str(
                response_payload.get("error")
                or response_payload.get("message")
                or detail
            )

        raise UpstreamFunctionError(
            status_code=response.status_code,
            detail=detail,
            payload=response_payload,
        )

    return response_payload
