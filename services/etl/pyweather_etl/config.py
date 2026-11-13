"""Configuração do ETL via variáveis de ambiente (pydantic-settings)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from pyweather_etl.domain.value_objects import Coordinates, LocationSpec


class Settings(BaseSettings):
    """Todas as variáveis são lidas do ambiente (no Docker, do ``.env`` do serviço)."""

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    # --- OpenWeather ---------------------------------------------------------
    openweather_api_key: SecretStr = SecretStr("fd9de68f6804568e0b270a220fd06b0f")
    openweather_base_url: str = "https://api.openweathermap.org"
    openweather_units: Literal["standard", "metric", "imperial"] = "metric"
    openweather_lang: str = "pt_br"
    http_timeout_seconds: float = Field(default=15.0, gt=0)
    http_max_retries: int = Field(default=3, ge=0, le=10)

    # --- Cidade-alvo ---------------------------------------------------------
    city_name: str = "Florianópolis"
    city_state: str | None = "Santa Catarina"
    city_country: str = "BR"
    # Se ambas forem informadas, a geocodificação é dispensada.
    city_latitude: float | None = None
    city_longitude: float | None = None

    # --- Extração ------------------------------------------------------------
    etl_interval_seconds: int = Field(default=3600, ge=60)
    etl_hourly_pages: int = Field(default=3, ge=0, le=10)
    etl_daily_pages: int = Field(default=1, ge=0, le=10)
    etl_include_alerts: bool = True

    # --- PostgreSQL ----------------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "pyweather"
    postgres_user: str = "pyweather"
    postgres_password: SecretStr = SecretStr("pyweather")
    # Se informada, tem precedência sobre as variáveis POSTGRES_* (útil em testes).
    database_url: str | None = None

    log_level: str = "INFO"

    @model_validator(mode="after")
    def _check_coordinates_pair(self) -> Settings:
        if (self.city_latitude is None) != (self.city_longitude is None):
            raise ValueError("Informe CITY_LATITUDE e CITY_LONGITUDE juntas (ou nenhuma).")
        return self

    @property
    def sqlalchemy_url(self) -> str | URL:
        """URL de conexão SQLAlchemy (driver psycopg 3)."""
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
    def location_spec(self) -> LocationSpec:
        coordinates = None
        if self.city_latitude is not None and self.city_longitude is not None:
            coordinates = Coordinates(self.city_latitude, self.city_longitude)
        return LocationSpec(
            name=self.city_name,
            country=self.city_country,
            state=self.city_state,
            coordinates=coordinates,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
