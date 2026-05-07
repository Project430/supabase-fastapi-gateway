"""User-scoped profile routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import get_bearer_token, get_user_id_from_token
from app.config import Settings, get_settings
from app.services.supabase_rest import UpstreamRestError, call_supabase_rest

router = APIRouter(prefix="/v1/profile", tags=["profile"])

TABLE = "profiles"
SELECT_COLUMNS = "id,user_id,display_name,avatar_url,locale,updated_at"


class ProfileUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    display_name: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=2_000)
    locale: str | None = Field(default=None, max_length=12)


def _err(exc: UpstreamRestError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@router.get("")
async def get_profile(
    token: str = Depends(get_bearer_token),
    settings: Settings = Depends(get_settings),
) -> Any:
    user_id = get_user_id_from_token(token)
    try:
        rows = await call_supabase_rest(
            settings=settings,
            method="GET",
            table=TABLE,
            token=token,
            query_params={
                "select": SELECT_COLUMNS,
                "user_id": f"eq.{user_id}",
                "limit": "1",
            },
        )
    except UpstreamRestError as exc:
        return _err(exc)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )
    return rows[0]


@router.patch("")
async def update_profile(
    body: ProfileUpdate,
    token: str = Depends(get_bearer_token),
    settings: Settings = Depends(get_settings),
) -> Any:
    user_id = get_user_id_from_token(token)
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    try:
        rows = await call_supabase_rest(
            settings=settings,
            method="PATCH",
            table=TABLE,
            token=token,
            query_params={"user_id": f"eq.{user_id}", "select": SELECT_COLUMNS},
            json_body=updates,
            prefer="return=representation",
        )
    except UpstreamRestError as exc:
        return _err(exc)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )
    return rows[0]
