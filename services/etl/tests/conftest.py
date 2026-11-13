"""Fixtures compartilhadas dos testes do ETL."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from pyweather_etl.infrastructure.persistence.database import create_session_factory
from pyweather_etl.infrastructure.persistence.schema import upgrade_to_head


FIXED_NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


@pytest.fixture
def engine() -> Iterator[Engine]:
    """SQLite em memória, migrado com o Alembic (mesmo caminho usado em produção)."""
    sqlite = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(sqlite, "connect")
    def _enable_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    upgrade_to_head(sqlite)
    yield sqlite
    sqlite.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


def _step(moment: datetime, **overrides: Any) -> dict[str, Any]:
    """Passo de 3 h no formato da 5 Day / 3 Hour Forecast (unidades métricas)."""
    record: dict[str, Any] = {
        "dt": int(moment.timestamp()),
        "main": {
            "temp": 24.0,
            "feels_like": 24.6,
            "temp_min": 23.0,
            "temp_max": 25.0,
            "pressure": 1017,
            "humidity": 70,
        },
        "weather": [{"id": 803, "main": "Clouds", "description": "nublado", "icon": "04d"}],
        "clouds": {"all": 60},
        "wind": {"speed": 3.8, "deg": 100, "gust": 6.0},
        "visibility": 9000,
        "pop": 0.35,
        "rain": {"3h": 0.5},
    }
    record.update(overrides)
    return record


@pytest.fixture
def current_payload() -> dict[str, Any]:
    """Resposta de ``/data/2.5/weather`` (unidades métricas)."""
    return {
        "coord": {"lon": -48.548, "lat": -27.5954},
        "weather": [{"id": 500, "main": "Rain", "description": "chuva leve", "icon": "10d"}],
        "main": {
            "temp": 24.5,
            "feels_like": 25.1,
            "temp_min": 23.0,
            "temp_max": 26.0,
            "pressure": 1018,
            "humidity": 70,
        },
        "visibility": 10000,
        "wind": {"speed": 4.2, "deg": 120, "gust": 7.1},
        "rain": {"1h": 0.4},
        "clouds": {"all": 40},
        "dt": 1_777_449_371,
        "sys": {"country": "BR", "sunrise": 1_777_437_375, "sunset": 1_777_490_344},
        "timezone": -10800,
        "name": "Florianópolis",
        "cod": 200,
    }


@pytest.fixture
def forecast_payload() -> dict[str, Any]:
    """Resposta de ``/data/2.5/forecast``: 4 passos em 2 dias civis locais (UTC-3).

    12/11: 12:00 e 15:00 locais; 13/11: 03:00 e 06:00 locais.
    """
    t0 = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)
    rainy = {"id": 500, "main": "Rain", "description": "chuva leve", "icon": "10d"}
    return {
        "cod": "200",
        "cnt": 4,
        "list": [
            _step(t0),
            _step(
                t0 + timedelta(hours=3),
                main={
                    "temp": 28.0,
                    "feels_like": 29.0,
                    "temp_min": 27.0,
                    "temp_max": 29.5,
                    "pressure": 1015,
                    "humidity": 60,
                },
                wind={"speed": 5.5, "deg": 90, "gust": 9.0},
                pop=0.8,
                rain={"3h": 1.25},
            ),
            _step(t0 + timedelta(hours=15), weather=[rainy], pop=0.2, rain={"3h": 0.25}),
            _step(
                t0 + timedelta(hours=18),
                weather=[rainy],
                pop=0.1,
                rain=None,
                clouds=None,
                wind=None,
                visibility=None,
            ),
        ],
        "city": {"name": "Florianópolis", "country": "BR", "timezone": -10800},
    }


@pytest.fixture
def geocoding_payload() -> list[dict[str, Any]]:
    return [
        {
            "name": "Florianópolis",
            "lat": -27.5954,
            "lon": -48.5480,
            "country": "BR",
            "state": "Santa Catarina",
        }
    ]
