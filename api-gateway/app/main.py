from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.functions import router as functions_router
from app.routes.profile import router as profile_router
from app.routes.storage import router as storage_router

settings = get_settings()

app = FastAPI(title="supabase-fastapi-gateway", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(settings.frontend_origin).rstrip("/")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/api", tags=["api"])
async def api_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(profile_router)
app.include_router(functions_router)
app.include_router(storage_router)
