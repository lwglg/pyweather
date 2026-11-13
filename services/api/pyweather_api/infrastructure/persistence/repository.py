"""Implementação SQLModel da porta de leitura."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement, Engine, func, text
from sqlmodel import Session, col, select

from pyweather_api.domain.models import (
    AlertDescription,
    AlertFilter,
    Condition,
    CurrentFilter,
    CurrentWeather,
    DailyFilter,
    DailyForecast,
    HourlyFilter,
    HourlyForecast,
    Location,
    LocationFilter,
    Page,
    Pagination,
    SortOrder,
    TimeRange,
    WeatherAlert,
)
from pyweather_api.domain.ports import WeatherReadRepository
from pyweather_api.infrastructure.persistence.tables import (
    CurrentWeatherTable,
    DailyForecastTable,
    HourlyForecastTable,
    LocationTable,
    WeatherAlertTable,
)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _utc_opt(value: datetime | None) -> datetime | None:
    return None if value is None else _utc(value)


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _condition(row: Any) -> Condition:
    return Condition(
        code=row.condition_code,
        main=row.condition_main,
        description=row.condition_description,
        icon=row.condition_icon,
    )


def _period(column: Any, period: TimeRange) -> list[ColumnElement[bool]]:
    clauses: list[ColumnElement[bool]] = []
    if period.start is not None:
        clauses.append(col(column) >= period.start)
    if period.end is not None:
        clauses.append(col(column) <= period.end)
    return clauses


def _contains(column: Any, term: str) -> ColumnElement[bool]:
    return col(column).ilike(_like(term), escape="\\")


def _condition_clause(table: Any, term: str | None) -> list[ColumnElement[bool]]:
    if not term:
        return []
    return [_contains(table.condition_main, term) | _contains(table.condition_description, term)]


class SqlModelWeatherReadRepository(WeatherReadRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # --- Locais --------------------------------------------------------------------------------
    def list_locations(self, flt: LocationFilter, page: Pagination) -> Page[Location]:
        clauses: list[ColumnElement[bool]] = []
        if flt.name:
            clauses.append(_contains(LocationTable.name, flt.name))
        if flt.state:
            clauses.append(_contains(LocationTable.state, flt.state))
        if flt.country:
            clauses.append(func.upper(col(LocationTable.country)) == flt.country.upper())
        ordering = [col(LocationTable.name), col(LocationTable.id)]
        return self._page(LocationTable, clauses, ordering, page, self._to_location)

    def get_location(self, location_id: int) -> Location | None:
        with Session(self._engine) as session:
            row = session.get(LocationTable, location_id)
            return None if row is None else self._to_location(row)

    # --- Condições atuais ----------------------------------------------------------------------
    def latest_current(self, location_id: int) -> CurrentWeather | None:
        with Session(self._engine) as session:
            row = session.exec(
                select(CurrentWeatherTable)
                .where(CurrentWeatherTable.location_id == location_id)
                .order_by(col(CurrentWeatherTable.observed_at).desc())
                .limit(1)
            ).first()
            return None if row is None else self._to_current(row)

    def list_current(
        self, location_id: int, flt: CurrentFilter, page: Pagination
    ) -> Page[CurrentWeather]:
        t = CurrentWeatherTable
        clauses = [col(t.location_id) == location_id, *_period(t.observed_at, flt.period)]
        if flt.min_temperature is not None:
            clauses.append(col(t.temperature) >= flt.min_temperature)
        if flt.max_temperature is not None:
            clauses.append(col(t.temperature) <= flt.max_temperature)
        if flt.min_humidity is not None:
            clauses.append(col(t.humidity) >= flt.min_humidity)
        if flt.max_humidity is not None:
            clauses.append(col(t.humidity) <= flt.max_humidity)
        clauses += _condition_clause(t, flt.condition)
        ordering = [self._order(t.observed_at, flt.order)]
        return self._page(t, clauses, ordering, page, self._to_current)

    # --- Previsões -----------------------------------------------------------------------------
    def list_hourly(
        self, location_id: int, flt: HourlyFilter, page: Pagination
    ) -> Page[HourlyForecast]:
        t = HourlyForecastTable
        clauses = [col(t.location_id) == location_id, *_period(t.forecast_at, flt.period)]
        if flt.min_temperature is not None:
            clauses.append(col(t.temperature) >= flt.min_temperature)
        if flt.max_temperature is not None:
            clauses.append(col(t.temperature) <= flt.max_temperature)
        if flt.min_pop is not None:
            clauses.append(col(t.pop) >= flt.min_pop)
        clauses += _condition_clause(t, flt.condition)
        ordering = [self._order(t.forecast_at, flt.order)]
        return self._page(t, clauses, ordering, page, self._to_hourly)

    def list_daily(
        self, location_id: int, flt: DailyFilter, page: Pagination
    ) -> Page[DailyForecast]:
        t = DailyForecastTable
        clauses = [col(t.location_id) == location_id, *_period(t.forecast_at, flt.period)]
        if flt.min_temperature is not None:
            clauses.append(col(t.temp_min) >= flt.min_temperature)
        if flt.max_temperature is not None:
            clauses.append(col(t.temp_max) <= flt.max_temperature)
        if flt.min_pop is not None:
            clauses.append(col(t.pop) >= flt.min_pop)
        clauses += _condition_clause(t, flt.condition)
        ordering = [self._order(t.forecast_at, flt.order)]
        return self._page(t, clauses, ordering, page, self._to_daily)

    # --- Alertas -------------------------------------------------------------------------------
    def list_alerts(
        self, location_id: int, flt: AlertFilter, page: Pagination
    ) -> Page[WeatherAlert]:
        t = WeatherAlertTable
        clauses: list[ColumnElement[bool]] = [col(t.location_id) == location_id]
        if flt.event:
            clauses.append(_contains(t.event, flt.event))
        if flt.sender:
            clauses.append(_contains(t.sender_name, flt.sender))
        if flt.active_at is not None:
            clauses.append(col(t.starts_at) <= flt.active_at)
            clauses.append(col(t.ends_at) >= flt.active_at)
        ordering = [self._order(t.starts_at, flt.order)]
        return self._page(t, clauses, ordering, page, self._to_alert)

    # --- Saúde ---------------------------------------------------------------------------------
    def ping(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            return False
        return True

    # --- Internos ------------------------------------------------------------------------------
    @staticmethod
    def _order(column: Any, order: SortOrder) -> Any:
        return col(column).asc() if order is SortOrder.ASC else col(column).desc()

    def _page[M](
        self,
        table: type[Any],
        clauses: list[Any],
        ordering: list[Any],
        page: Pagination,
        mapper: Callable[[Any], M],
    ) -> Page[M]:
        with Session(self._engine) as session:
            total = session.exec(select(func.count()).select_from(table).where(*clauses)).one()
            rows = session.exec(
                select(table)
                .where(*clauses)
                .order_by(*ordering)
                .offset(page.offset)
                .limit(page.limit)
            ).all()
        return Page(
            items=tuple(mapper(row) for row in rows),
            total=int(total),
            limit=page.limit,
            offset=page.offset,
        )

    @staticmethod
    def _to_location(row: LocationTable) -> Location:
        return Location(
            id=row.id,
            name=row.name,
            state=row.state,
            country=row.country,
            latitude=row.latitude,
            longitude=row.longitude,
            timezone=row.timezone,
            timezone_offset=row.timezone_offset,
        )

    @staticmethod
    def _to_current(row: CurrentWeatherTable) -> CurrentWeather:
        return CurrentWeather(
            location_id=row.location_id,
            observed_at=_utc(row.observed_at),
            temperature=row.temperature,
            feels_like=row.feels_like,
            pressure=row.pressure,
            humidity=row.humidity,
            dew_point=row.dew_point,
            uvi=row.uvi,
            clouds=row.clouds,
            visibility=row.visibility,
            wind_speed=row.wind_speed,
            wind_deg=row.wind_deg,
            wind_gust=row.wind_gust,
            rain_1h=row.rain_1h,
            snow_1h=row.snow_1h,
            condition=_condition(row),
            sunrise=_utc_opt(row.sunrise),
            sunset=_utc_opt(row.sunset),
            fetched_at=_utc(row.fetched_at),
        )

    @staticmethod
    def _to_hourly(row: HourlyForecastTable) -> HourlyForecast:
        return HourlyForecast(
            location_id=row.location_id,
            forecast_at=_utc(row.forecast_at),
            temperature=row.temperature,
            feels_like=row.feels_like,
            pressure=row.pressure,
            humidity=row.humidity,
            dew_point=row.dew_point,
            uvi=row.uvi,
            clouds=row.clouds,
            visibility=row.visibility,
            wind_speed=row.wind_speed,
            wind_deg=row.wind_deg,
            wind_gust=row.wind_gust,
            rain_1h=row.rain_1h,
            snow_1h=row.snow_1h,
            pop=row.pop,
            condition=_condition(row),
            fetched_at=_utc(row.fetched_at),
        )

    @staticmethod
    def _to_daily(row: DailyForecastTable) -> DailyForecast:
        return DailyForecast(
            location_id=row.location_id,
            forecast_at=_utc(row.forecast_at),
            temp_day=row.temp_day,
            temp_min=row.temp_min,
            temp_max=row.temp_max,
            temp_night=row.temp_night,
            temp_eve=row.temp_eve,
            temp_morn=row.temp_morn,
            feels_like_day=row.feels_like_day,
            feels_like_night=row.feels_like_night,
            feels_like_eve=row.feels_like_eve,
            feels_like_morn=row.feels_like_morn,
            pressure=row.pressure,
            humidity=row.humidity,
            dew_point=row.dew_point,
            uvi=row.uvi,
            clouds=row.clouds,
            wind_speed=row.wind_speed,
            wind_deg=row.wind_deg,
            wind_gust=row.wind_gust,
            rain=row.rain,
            snow=row.snow,
            pop=row.pop,
            condition=_condition(row),
            sunrise=_utc_opt(row.sunrise),
            sunset=_utc_opt(row.sunset),
            moonrise=_utc_opt(row.moonrise),
            moonset=_utc_opt(row.moonset),
            moon_phase=row.moon_phase,
            fetched_at=_utc(row.fetched_at),
        )

    @staticmethod
    def _to_alert(row: WeatherAlertTable) -> WeatherAlert:
        return WeatherAlert(
            location_id=row.location_id,
            alert_id=row.alert_id,
            sender_name=row.sender_name,
            event=row.event,
            starts_at=_utc(row.starts_at),
            ends_at=_utc(row.ends_at),
            descriptions=tuple(
                AlertDescription(
                    language=d.get("language", ""), description=d.get("description", "")
                )
                for d in row.descriptions
            ),
            tags=tuple(row.tags),
            fetched_at=_utc(row.fetched_at),
        )
