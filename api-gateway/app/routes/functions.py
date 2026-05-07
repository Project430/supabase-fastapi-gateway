"""One explicit route per Edge Function."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import get_bearer_token
from app.config import Settings, get_settings
from app.services.supabase_functions import (
    UpstreamFunctionError,
    invoke_supabase_function,
)

router = APIRouter(prefix="/v1/functions", tags=["functions"])


class ExampleFunctionRequest(BaseModel):
    model_config = {"extra": "forbid"}

    input_text: str = Field(min_length=1, max_length=20_000)
    options: dict[str, Any] | None = None


@router.post("/example")
async def call_example_function(
    body: ExampleFunctionRequest,
    token: str = Depends(get_bearer_token),
    settings: Settings = Depends(get_settings),
) -> Any:
    try:
        result = await invoke_supabase_function(
            settings=settings,
            function_name="example-function",
            token=token,
            payload=body.model_dump(),
        )
    except UpstreamFunctionError as exc:
        content: dict[str, Any] = {"detail": exc.detail}
        if exc.payload is not None:
            content["upstream"] = exc.payload
        return JSONResponse(status_code=exc.status_code, content=content)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Edge Function returned no payload.",
        )
    return result
