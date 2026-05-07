from functools import lru_cache

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: AnyHttpUrl
    supabase_anon_key: str
    frontend_origin: AnyHttpUrl

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def function_url(self, function_name: str) -> str:
        return f"{str(self.supabase_url).rstrip('/')}/functions/v1/{function_name}"

    def rest_url(self, table: str) -> str:
        return f"{str(self.supabase_url).rstrip('/')}/rest/v1/{table}"

    def storage_public_url(self, bucket: str, path: str) -> str:
        base = str(self.supabase_url).rstrip("/")
        return f"{base}/storage/v1/object/public/{bucket}/{path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
