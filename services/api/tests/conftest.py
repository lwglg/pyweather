"""Fixtures da API: SQLite em memória com dados de exemplo e cliente HTTP."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from pyweather_api.config import Settings
from pyweather_api.infrastructure.persistence.repository import SqlModelWeatherReadRepository
from pyweather_api.infrastructure.persistence.tables import (
    CurrentWeatherTable,
    DailyForecastTable,
    HourlyForecastTable,
    LocationTable,
    WeatherAlertTable,
)
from pyweather_api.main import create_app


T0 = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


@pytest.fixture
def engine() -> Iterator[Engine]:
    sqlite = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(sqlite)
    with Session(sqlite) as session:
        _seed(session)
    yield sqlite
    sqlite.dispose()


def _seed(session: Session) -> None:
    session.add(
        LocationTable(
            id=1,
            name="Florianópolis",
            state="Santa Catarina",
            country="BR",
            latitude=-27.5954,
            longitude=-48.548,
            timezone="America/Sao_Paulo",
            timezone_offset=-10800,
            created_at=T0,
            updated_at=T0,
        )
    )
    session.add(
        LocationTable(
            id=2,
            name="Curitiba",
            state="Paraná",
            country="BR",
            latitude=-25.4284,
            longitude=-49.2733,
            created_at=T0,
            updated_at=T0,
        )
    )
    session.add(
        LocationTable(
            id=3,
            name="Austin",
            state="Texas",
            country="US",
            latitude=30.2672,
            longitude=-97.7431,
            created_at=T0,
            updated_at=T0,
        )
    )
    for i in range(5):
        session.add(
            CurrentWeatherTable(
                location_id=1,
                observed_at=T0 + timedelta(hours=i),
                temperature=20.0 + i * 2,  # 20, 22, 24, 26, 28
                feels_like=21.0 + i * 2,
                pressure=1015,
                humidity=50 + i * 10,  # 50 .. 90
                wind_speed=3.0,
                condition_code=500 if i % 2 == 0 else 800,
                condition_main="Rain" if i % 2 == 0 else "Clear",
                condition_description="chuva leve" if i % 2 == 0 else "céu limpo",
                condition_icon="10d",
                sunrise=T0,
                fetched_at=T0,
            )
        )
        session.add(
            HourlyForecastTable(
                location_id=1,
                forecast_at=T0 + timedelta(hours=i),
                temperature=18.0 + i,
                feels_like=18.0,
                pressure=1012,
                humidity=60,
                pop=i / 4,  # 0, .25, .5, .75, 1
                condition_main="Clouds",
                condition_description="nublado",
                fetched_at=T0,
            )
        )
        session.add(
            DailyForecastTable(
                location_id=1,
                forecast_at=T0 + timedelta(days=i),
                temp_min=15.0 + i,
                temp_max=25.0 + i,
                pop=i / 4,
                condition_main="Clear",
                condition_description="céu limpo",
                moon_phase=0.5,
                fetched_at=T0,
            )
        )
    session.add(
        WeatherAlertTable(
            location_id=1,
            alert_id="A1",
            sender_name="INMET",
            event="Tempestade",
            starts_at=T0,
            ends_at=T0 + timedelta(hours=6),
            descriptions=[{"language": "pt-BR", "description": "Chuvas intensas."}],
            tags=["Rain"],
            fetched_at=T0,
        )
    )
    session.add(
        WeatherAlertTable(
            location_id=1,
            alert_id="A2",
            sender_name="Defesa Civil",
            event="Vendaval",
            starts_at=T0 + timedelta(days=1),
            ends_at=T0 + timedelta(days=2),
            descriptions=[],
            tags=[],
            fetched_at=T0,
        )
    )
    session.commit()


@pytest.fixture
def repository(engine: Engine) -> SqlModelWeatherReadRepository:
    return SqlModelWeatherReadRepository(engine)


@pytest.fixture
def client(repository: SqlModelWeatherReadRepository) -> Iterator[TestClient]:
    app = create_app(Settings(), repository=repository)
    with TestClient(app) as test_client:
        yield test_client
