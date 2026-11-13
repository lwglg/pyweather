"""Configuração da API via variáveis de ambiente."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "pyweather"
    postgres_user: str = "pyweather"
    postgres_password: SecretStr = SecretStr("pyweather")
    database_url: str | None = None

    api_title: str = "pyweather API"
    api_root_path: str = ""
    cors_origins: str = ""  # lista separada por vírgulas; vazio = CORS desabilitado
    log_level: str = "INFO"

    @property
    def sqlalchemy_url(self) -> str | URL:
        if self.database_url:
            return self.database_url
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
