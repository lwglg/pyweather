"""Fábrica da aplicação FastAPI."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from pyweather_api import __version__
from pyweather_api.application.services import WeatherQueryService
from pyweather_api.config import Settings, get_settings
from pyweather_api.domain.ports import WeatherReadRepository
from pyweather_api.infrastructure.persistence.repository import SqlModelWeatherReadRepository
from pyweather_api.presentation.api.errors import register_error_handlers
from pyweather_api.presentation.api.routers import health, locations


DESCRIPTION = """
API RESTful para consulta de **dados climáticos** extraídos da OpenWeather (One Call API 4.0)
e armazenados em PostgreSQL pelo serviço de ETL do projeto **pyweather**.

* **Locais**: cidades monitoradas.
* **Condições atuais**: observação mais recente e histórico acumulado.
* **Previsões**: séries horária e diária.
* **Alertas**: avisos meteorológicos oficiais.

Todas as listagens são paginadas (`limit`/`offset`) e aceitam filtros específicos.
Datas e horas são sempre retornadas em UTC (ISO 8601).
"""

TAGS = [
    {
        "name": "Locais e dados climáticos",
        "description": "Consulta de locais, condições, previsões e alertas.",
    },
    {"name": "Saúde", "description": "Verificações de disponibilidade do serviço."},
]


def create_app(
    settings: Settings | None = None,
    repository: WeatherReadRepository | None = None,
) -> FastAPI:
    """Cria a aplicação. ``repository`` permite injetar uma implementação nos testes."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(level=settings.log_level.upper())
        if repository is not None:
            app.state.service = WeatherQueryService(repository)
            yield
            return
        engine = create_engine(settings.sqlalchemy_url, pool_pre_ping=True)
        app.state.service = WeatherQueryService(SqlModelWeatherReadRepository(engine))
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title=settings.api_title,
        version=__version__,
        description=DESCRIPTION,
        openapi_tags=TAGS,
        root_path=settings.api_root_path,
        lifespan=lifespan,
    )
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET"],
            allow_headers=["*"],
        )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(locations.router)
    return app


app = create_app()
