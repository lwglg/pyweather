"""Fixtures compartilhadas dos testes do ETL."""

from collections.abc import Iterator
from datetime import UTC, datetime
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


@pytest.fixture
def weather_record() -> dict[str, Any]:
    """Registro de condições atuais (formato One Call 4.0, unidades métricas)."""
    return {
        "dt": 1_777_449_371,
        "sunrise": 1_777_437_375,
        "sunset": 1_777_490_344,
        "temp": 24.5,
        "feels_like": 25.1,
        "pressure": 1018,
        "humidity": 70,
        "dew_point": 18.2,
        "uvi": 5.5,
        "clouds": 40,
        "visibility": 10000,
        "wind_speed": 4.2,
        "wind_deg": 120,
        "wind_gust": 7.1,
        "rain": {"1h": 0.4},
        "weather": [{"id": 500, "main": "Rain", "description": "chuva leve", "icon": "10d"}],
        "alerts": ["ALERT-1", "ALERT-2"],
    }


@pytest.fixture
def current_payload(weather_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "lat": -27.6,
        "lon": -48.5,
        "timezone": "America/Sao_Paulo",
        "timezone_offset": -10800,
        "data": [weather_record],
    }


@pytest.fixture
def hourly_record() -> dict[str, Any]:
    return {
        "dt": 1_777_453_200,
        "temp": 23.9,
        "feels_like": 24.4,
        "pressure": 1017,
        "humidity": 75,
        "dew_point": 19.0,
        "uvi": 3.2,
        "clouds": 60,
        "visibility": 9000,
        "wind_speed": 3.8,
        "wind_deg": 100,
        "pop": 0.35,
        "rain": {"1h": 0.2},
        "weather": [{"id": 803, "main": "Clouds", "description": "nublado", "icon": "04d"}],
    }


@pytest.fixture
def daily_record() -> dict[str, Any]:
    return {
        "dt": 1_777_460_400,
        "sunrise": 1_777_437_375,
        "sunset": 1_777_490_344,
        "moonrise": 1_777_482_960,
        "moonset": 1_777_433_400,
        "moon_phase": 0.43,
        "temp": {"day": 26.0, "min": 20.1, "max": 28.3, "night": 21.5, "eve": 25.0, "morn": 21.0},
        "feels_like": {"day": 27.0, "night": 21.9, "eve": 25.6, "morn": 21.2},
        "pressure": 1016,
        "humidity": 68,
        "dew_point": 19.5,
        "wind_speed": 5.1,
        "wind_deg": 90,
        "wind_gust": 9.9,
        "weather": [{"id": 800, "main": "Clear", "description": "céu limpo", "icon": "01d"}],
        "clouds": 5,
        "pop": 0.1,
        "uvi": 9.8,
        "rain": 1.5,
    }


@pytest.fixture
def alert_payload() -> dict[str, Any]:
    return {
        "id": "ALERT-1",
        "sender_name": "INMET",
        "event": "Tempestade",
        "start": 1_787_817_940,
        "end": 1_787_868_000,
        "description": [
            {"language": "pt-BR", "description": "Chuvas intensas."},
            {"language": "en-GB", "description": "Heavy rain."},
        ],
        "tags": ["Thunderstorm", "Rain"],
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
