"""Application settings — secrets from .env; ports from application.properties only."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from infrastructure.application_properties import (
    get_backend_port,
    get_frontend_port,
    get_properties_file_path,
    load_application_properties,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "VeloMatrix"
    debug: bool = False
    database_url: str = ""
    anthropic_api_key: str = ""
    admin_api_key: str = ""
    # Set VELOMATRIX_ADMIN_API_KEY (or ADMIN_API_KEY) in .env for production

    @property
    def backend_port(self) -> int:
        return get_backend_port()

    @property
    def frontend_port(self) -> int:
        return get_frontend_port()

    @property
    def cors_origin_list(self) -> list[str]:
        fp = get_frontend_port()
        origins = [
            f"http://localhost:{fp}",
            f"http://127.0.0.1:{fp}",
        ]
        extra = load_application_properties().get("cors.extra.origins", "").strip()
        if extra:
            origins.extend([x.strip() for x in extra.split(",") if x.strip()])
        return origins

    @property
    def application_properties_path(self) -> str | None:
        return get_properties_file_path()


@lru_cache
def get_settings() -> Settings:
    return Settings()
