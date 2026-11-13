"""Raiz de composição: monta as dependências concretas do caso de uso."""

import logging

from sqlalchemy import Engine

from pyweather_etl.application.use_cases import SyncOptions, SyncWeatherUseCase
from pyweather_etl.config import Settings
from pyweather_etl.infrastructure.openweather.client import OpenWeatherClient
from pyweather_etl.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
)
from pyweather_etl.infrastructure.persistence.repositories import SqlAlchemyWeatherRepository


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    # As URLs de requisição contêm a chave (appid): nunca registrar em nível INFO.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def build_engine(settings: Settings) -> Engine:
    return create_db_engine(settings.sqlalchemy_url)


def build_use_case(
    settings: Settings, engine: Engine
) -> tuple[SyncWeatherUseCase, OpenWeatherClient]:
    """Retorna o caso de uso e o cliente HTTP (para que o chamador o feche)."""
    client = OpenWeatherClient(
        settings.openweather_api_key.get_secret_value(),
        base_url=settings.openweather_base_url,
        units=settings.openweather_units,
        lang=settings.openweather_lang,
        timeout=settings.http_timeout_seconds,
        max_retries=settings.http_max_retries,
    )
    repository = SqlAlchemyWeatherRepository(create_session_factory(engine))
    use_case = SyncWeatherUseCase(
        geocoder=client,
        provider=client,
        repository=repository,
        spec=settings.location_spec,
        options=SyncOptions(
            hourly_pages=settings.etl_hourly_pages,
            daily_pages=settings.etl_daily_pages,
            include_alerts=settings.etl_include_alerts,
        ),
    )
    return use_case, client
