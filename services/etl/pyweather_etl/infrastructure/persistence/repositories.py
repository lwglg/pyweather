"""Implementação SQLAlchemy da porta ``WeatherRepository``."""

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from pyweather_etl.domain.entities import (
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    Location,
    WeatherAlert,
)
from pyweather_etl.domain.ports import WeatherRepository
from pyweather_etl.domain.value_objects import TimezoneInfo
from pyweather_etl.infrastructure.persistence.models import Base, LocationModel
from pyweather_etl.infrastructure.persistence.row_mappers import (
    to_alert_row,
    to_current_row,
    to_daily_row,
    to_hourly_row,
)


_COORDINATE_DECIMALS = 6  # precisão da coluna NUMERIC(9, 6)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SqlAlchemyWeatherRepository(WeatherRepository):
    """Cada operação é uma transação própria; gravações usam ``merge`` (upsert por chave)."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock

    def upsert_location(self, location: Location) -> Location:
        now = self._clock()
        latitude = round(location.coordinates.latitude, _COORDINATE_DECIMALS)
        longitude = round(location.coordinates.longitude, _COORDINATE_DECIMALS)

        with self._session_factory.begin() as session:
            row = session.scalar(
                select(LocationModel).where(
                    LocationModel.latitude == latitude, LocationModel.longitude == longitude
                )
            )
            if row is None:
                row = LocationModel(
                    latitude=latitude, longitude=longitude, created_at=now, updated_at=now
                )
                session.add(row)
            row.name = location.name
            row.state = location.state
            row.country = location.country
            row.updated_at = now
            if location.timezone is not None:
                row.timezone = location.timezone.name
                row.timezone_offset = location.timezone.offset_seconds
            session.flush()
            return replace(location, id=row.id)

    def update_timezone(self, location_id: int, timezone: TimezoneInfo) -> None:
        with self._session_factory.begin() as session:
            row = session.get(LocationModel, location_id)
            if row is not None:
                row.timezone = timezone.name
                row.timezone_offset = timezone.offset_seconds

    def save_current(self, location_id: int, weather: CurrentWeather) -> int:
        return self._merge_all([to_current_row(location_id, weather, self._clock())])

    def save_hourly(self, location_id: int, forecasts: Sequence[HourlyForecast]) -> int:
        now = self._clock()
        return self._merge_all([to_hourly_row(location_id, item, now) for item in forecasts])

    def save_daily(self, location_id: int, forecasts: Sequence[DailyForecast]) -> int:
        now = self._clock()
        return self._merge_all([to_daily_row(location_id, item, now) for item in forecasts])

    def save_alerts(self, location_id: int, alerts: Sequence[WeatherAlert]) -> int:
        now = self._clock()
        return self._merge_all([to_alert_row(location_id, item, now) for item in alerts])

    def _merge_all(self, rows: Sequence[Base]) -> int:
        if not rows:
            return 0
        with self._session_factory.begin() as session:
            for row in rows:
                session.merge(row)
        return len(rows)
