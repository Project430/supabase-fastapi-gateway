"""Public storage object passthrough.

Streams a file out of a single, allow-listed public bucket. Path traversal is
blocked: `..` is rejected. If you need private buckets or per-user files, do
not extend this route // write a new one that issues a Supabase signed URL
after checking the caller's permissions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.services.supabase_storage import (
    UpstreamStorageError,
    open_public_object_stream,
)

router = APIRouter(prefix="/v1/storage", tags=["storage"])

PUBLIC_BUCKET = "public-assets"


@router.get("/public/{object_path:path}")
async def get_public_object(
    object_path: str,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    if not object_path or ".." in object_path.split("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid object path.",
        )

    try:
        iterator, headers = await open_public_object_stream(
            settings=settings,
            bucket=PUBLIC_BUCKET,
            path=object_path,
        )
    except UpstreamStorageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return StreamingResponse(
        iterator,
        media_type=headers.get("content-type", "application/octet-stream"),
        headers={
            k: v
            for k, v in headers.items()
            if k in {"content-length", "cache-control", "etag"}
        },
    )
