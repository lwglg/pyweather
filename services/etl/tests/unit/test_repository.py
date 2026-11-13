from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from pyweather_etl.domain.entities import (
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    Location,
    WeatherAlert,
)
from pyweather_etl.domain.value_objects import (
    AlertDescription,
    Coordinates,
    DailyFeelsLike,
    DailyTemperature,
    Precipitation,
    TimezoneInfo,
    WeatherCondition,
    Wind,
)
from pyweather_etl.infrastructure.persistence.models import (
    CurrentWeatherModel,
    DailyForecastModel,
    HourlyForecastModel,
    LocationModel,
    UtcDateTime,
    WeatherAlertModel,
)
from pyweather_etl.infrastructure.persistence.repositories import SqlAlchemyWeatherRepository
from pyweather_etl.infrastructure.persistence.schema import head_revision, is_up_to_date


T0 = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
CLOCK_TIMES = iter(T0 + timedelta(minutes=i) for i in range(1000))
LOCATION = Location("Florianópolis", "BR", Coordinates(-27.5954, -48.548), state="Santa Catarina")


@pytest.fixture
def repository(session_factory: sessionmaker[Session]) -> SqlAlchemyWeatherRepository:
    return SqlAlchemyWeatherRepository(session_factory, clock=lambda: next(CLOCK_TIMES))


def count(session_factory: sessionmaker[Session], model: type) -> int:
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


def test_migracao_esta_atualizada(engine: Engine) -> None:
    assert head_revision() == "0001"
    assert is_up_to_date(engine)


def test_upsert_location_cria_e_reutiliza(
    repository: SqlAlchemyWeatherRepository, session_factory: sessionmaker[Session]
) -> None:
    first = repository.upsert_location(LOCATION)
    again = repository.upsert_location(
        Location("Florianópolis (atualizado)", "BR", Coordinates(-27.5954, -48.548))
    )

    assert first.id is not None
    assert again.id == first.id
    assert count(session_factory, LocationModel) == 1
    with session_factory() as session:
        row = session.get(LocationModel, first.id)
        assert row is not None
        assert row.name == "Florianópolis (atualizado)"
        assert row.updated_at > row.created_at


def test_upsert_location_com_timezone(
    repository: SqlAlchemyWeatherRepository, session_factory: sessionmaker[Session]
) -> None:
    location = repository.upsert_location(
        Location("X", "BR", Coordinates(1.0, 2.0), timezone=TimezoneInfo("UTC", 0))
    )
    with session_factory() as session:
        row = session.get(LocationModel, location.id)
        assert row is not None
        assert (row.timezone, row.timezone_offset) == ("UTC", 0)


def test_update_timezone(
    repository: SqlAlchemyWeatherRepository, session_factory: sessionmaker[Session]
) -> None:
    location = repository.upsert_location(LOCATION)
    assert location.id is not None

    repository.update_timezone(location.id, TimezoneInfo("America/Sao_Paulo", -10800))
    repository.update_timezone(9999, TimezoneInfo("UTC", 0))  # inexistente: sem efeito

    with session_factory() as session:
        row = session.get(LocationModel, location.id)
        assert row is not None
        assert (row.timezone, row.timezone_offset) == ("America/Sao_Paulo", -10800)


def current(temperature: float = 24.0, observed_at: datetime = T0) -> CurrentWeather:
    return CurrentWeather(
        observed_at=observed_at,
        temperature=temperature,
        feels_like=25.0,
        pressure=1015,
        humidity=60,
        wind=Wind(speed=3.0, direction=90, gust=5.0),
        precipitation=Precipitation(rain=0.5),
        condition=WeatherCondition(500, "Rain", "chuva leve", "10d"),
        sunrise=T0,
    )


def test_save_current_e_idempotente(
    repository: SqlAlchemyWeatherRepository, session_factory: sessionmaker[Session]
) -> None:
    location_id = repository.upsert_location(LOCATION).id
    assert location_id is not None

    assert repository.save_current(location_id, current(24.0)) == 1
    assert repository.save_current(location_id, current(26.5)) == 1  # mesmo instante: atualiza
    repository.save_current(location_id, current(20.0, T0 + timedelta(hours=1)))

    assert count(session_factory, CurrentWeatherModel) == 2
    with session_factory() as session:
        row = session.get(CurrentWeatherModel, (location_id, T0))
        assert row is not None
        assert row.temperature == 26.5
        assert row.condition_description == "chuva leve"
        assert row.rain_1h == 0.5
        assert row.wind_deg == 90
        assert row.sunrise == T0
        assert row.observed_at.tzinfo is not None


def test_save_hourly_e_daily(
    repository: SqlAlchemyWeatherRepository, session_factory: sessionmaker[Session]
) -> None:
    location_id = repository.upsert_location(LOCATION).id
    assert location_id is not None
    hourly = [
        HourlyForecast(
            forecast_at=T0 + timedelta(hours=i),
            temperature=20.0 + i,
            feels_like=20.0,
            pressure=1010,
            humidity=50,
            precipitation=Precipitation(probability=0.2),
        )
        for i in range(3)
    ]
    daily = [
        DailyForecast(
            forecast_at=T0,
            temperature=DailyTemperature(day=25.0, min=19.0, max=29.0),
            feels_like=DailyFeelsLike(day=26.0),
            precipitation=Precipitation(rain=2.0, probability=0.7),
            moon_phase=0.5,
        )
    ]

    assert repository.save_hourly(location_id, hourly) == 3
    assert repository.save_hourly(location_id, hourly) == 3  # reprocessamento
    assert repository.save_daily(location_id, daily) == 1

    assert count(session_factory, HourlyForecastModel) == 3
    with session_factory() as session:
        row = session.get(DailyForecastModel, (location_id, T0))
        assert row is not None
        assert (row.temp_min, row.temp_max, row.rain, row.pop) == (19.0, 29.0, 2.0, 0.7)
        assert row.feels_like_day == 26.0


def test_save_alerts(
    repository: SqlAlchemyWeatherRepository, session_factory: sessionmaker[Session]
) -> None:
    location_id = repository.upsert_location(LOCATION).id
    assert location_id is not None
    alert = WeatherAlert(
        "A1",
        "INMET",
        "Tempestade",
        T0,
        T0 + timedelta(hours=6),
        descriptions=(AlertDescription("pt-BR", "Chuvas intensas."),),
        tags=("Rain",),
    )

    assert repository.save_alerts(location_id, [alert]) == 1
    assert repository.save_alerts(location_id, [alert]) == 1

    assert count(session_factory, WeatherAlertModel) == 1
    with session_factory() as session:
        row = session.get(WeatherAlertModel, (location_id, "A1"))
        assert row is not None
        assert row.descriptions == [{"language": "pt-BR", "description": "Chuvas intensas."}]
        assert row.tags == ["Rain"]


def test_listas_vazias_nao_gravam(repository: SqlAlchemyWeatherRepository) -> None:
    assert repository.save_hourly(1, []) == 0
    assert repository.save_daily(1, []) == 0
    assert repository.save_alerts(1, []) == 0


def test_utc_datetime_rejeita_data_sem_fuso() -> None:
    with pytest.raises(ValueError, match="fuso"):
        UtcDateTime().process_bind_param(datetime(2026, 1, 1), None)  # type: ignore[arg-type]  # noqa: DTZ001


def test_utc_datetime_converte_para_utc() -> None:
    column = UtcDateTime()
    assert column.process_bind_param(None, None) is None  # type: ignore[arg-type]
    assert column.process_result_value(None, None) is None  # type: ignore[arg-type]
    naive = datetime(2026, 1, 1, 12)  # noqa: DTZ001
    assert column.process_result_value(naive, None).tzinfo is UTC  # type: ignore[arg-type, union-attr]
