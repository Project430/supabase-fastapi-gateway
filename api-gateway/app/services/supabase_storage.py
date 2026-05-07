"""Streaming proxy for public Supabase Storage objects.

Only public buckets are exposed here. Private buckets need signed URLs and a
different code path that you should design explicitly: do not generalize this
helper to "any object" without thinking about authorization.
"""

from typing import AsyncIterator

import httpx

from app.config import Settings


class UpstreamStorageError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def open_public_object_stream(
    *,
    settings: Settings,
    bucket: str,
    path: str,
) -> tuple[AsyncIterator[bytes], dict[str, str]]:
    """Return an async byte iterator for a public storage object plus a small
    set of forwarded headers (content-type, content-length, cache-control,
    etag). The iterator owns the underlying httpx client and closes it in its
    `finally` block, so the caller just consumes it.
    """
    headers = {"apikey": settings.supabase_anon_key}
    url = settings.storage_public_url(bucket, path)
    timeout = httpx.Timeout(60.0, connect=10.0)

    client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
    try:
        request = client.build_request("GET", url, headers=headers)
        response = await client.send(request, stream=True)
    except httpx.RequestError as exc:
        await client.aclose()
        raise UpstreamStorageError(
            status_code=502,
            detail="Failed to reach the storage service.",
        ) from exc

    if response.is_error:
        try:
            await response.aread()
        finally:
            await response.aclose()
            await client.aclose()
        raise UpstreamStorageError(
            status_code=response.status_code,
            detail="Storage object not available.",
        )

    forwarded: dict[str, str] = {}
    for header in ("content-type", "content-length", "cache-control", "etag"):
        value = response.headers.get(header)
        if value is not None:
            forwarded[header] = value

    async def iterator() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_raw():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return iterator(), forwarded
