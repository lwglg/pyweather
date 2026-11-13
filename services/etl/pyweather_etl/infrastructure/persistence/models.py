"""Modelos relacionais (carga — L do ETL).

Chaves compostas naturais ``(location_id, <instante>)`` tornam a carga idempotente:
reprocessar o mesmo instante atualiza o registro em vez de duplicá-lo.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Dialect,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator[datetime]):
    """``timestamptz`` que sempre entrega e exige datas com fuso (UTC), inclusive no SQLite."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Datas sem fuso horário não são aceitas.")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    """Base declarativa (metadados usados pelo Alembic)."""

    type_annotation_map: dict[Any, Any] = {}  # noqa: RUF012


# --- Colunas reutilizáveis ----------------------------------------------------------------------
class _ConditionColumns:
    condition_code: Mapped[int | None] = mapped_column(Integer)
    condition_main: Mapped[str | None] = mapped_column(String(32))
    condition_description: Mapped[str | None] = mapped_column(String(128))
    condition_icon: Mapped[str | None] = mapped_column(String(8))


class _WindColumns:
    wind_speed: Mapped[float | None] = mapped_column(Float)
    wind_deg: Mapped[int | None] = mapped_column(Integer)
    wind_gust: Mapped[float | None] = mapped_column(Float)


class _HourlyLikeColumns(_ConditionColumns, _WindColumns):
    """Campos comuns às observações atuais e às previsões horárias."""

    temperature: Mapped[float] = mapped_column(Float)
    feels_like: Mapped[float] = mapped_column(Float)
    pressure: Mapped[int] = mapped_column(Integer)
    humidity: Mapped[int] = mapped_column(Integer)
    dew_point: Mapped[float | None] = mapped_column(Float)
    uvi: Mapped[float | None] = mapped_column(Float)
    clouds: Mapped[int | None] = mapped_column(Integer)
    visibility: Mapped[int | None] = mapped_column(Integer)
    rain_1h: Mapped[float | None] = mapped_column(Float)
    snow_1h: Mapped[float | None] = mapped_column(Float)


# --- Tabelas ------------------------------------------------------------------------------------
class LocationModel(Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("latitude", "longitude", name="uq_locations_coordinates"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(8))
    latitude: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False))
    longitude: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False))
    timezone: Mapped[str | None] = mapped_column(String(64))
    timezone_offset: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)


class CurrentWeatherModel(_HourlyLikeColumns, Base):
    __tablename__ = "current_weather"

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True
    )
    observed_at: Mapped[datetime] = mapped_column(UtcDateTime, primary_key=True)
    sunrise: Mapped[datetime | None] = mapped_column(UtcDateTime)
    sunset: Mapped[datetime | None] = mapped_column(UtcDateTime)
    fetched_at: Mapped[datetime] = mapped_column(UtcDateTime)


class HourlyForecastModel(_HourlyLikeColumns, Base):
    __tablename__ = "hourly_forecasts"

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True
    )
    forecast_at: Mapped[datetime] = mapped_column(UtcDateTime, primary_key=True)
    pop: Mapped[float | None] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(UtcDateTime)


class DailyForecastModel(_ConditionColumns, _WindColumns, Base):
    __tablename__ = "daily_forecasts"

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True
    )
    forecast_at: Mapped[datetime] = mapped_column(UtcDateTime, primary_key=True)
    temp_day: Mapped[float | None] = mapped_column(Float)
    temp_min: Mapped[float | None] = mapped_column(Float)
    temp_max: Mapped[float | None] = mapped_column(Float)
    temp_night: Mapped[float | None] = mapped_column(Float)
    temp_eve: Mapped[float | None] = mapped_column(Float)
    temp_morn: Mapped[float | None] = mapped_column(Float)
    feels_like_day: Mapped[float | None] = mapped_column(Float)
    feels_like_night: Mapped[float | None] = mapped_column(Float)
    feels_like_eve: Mapped[float | None] = mapped_column(Float)
    feels_like_morn: Mapped[float | None] = mapped_column(Float)
    pressure: Mapped[int | None] = mapped_column(Integer)
    humidity: Mapped[int | None] = mapped_column(Integer)
    dew_point: Mapped[float | None] = mapped_column(Float)
    uvi: Mapped[float | None] = mapped_column(Float)
    clouds: Mapped[int | None] = mapped_column(Integer)
    rain: Mapped[float | None] = mapped_column(Float)
    snow: Mapped[float | None] = mapped_column(Float)
    pop: Mapped[float | None] = mapped_column(Float)
    sunrise: Mapped[datetime | None] = mapped_column(UtcDateTime)
    sunset: Mapped[datetime | None] = mapped_column(UtcDateTime)
    moonrise: Mapped[datetime | None] = mapped_column(UtcDateTime)
    moonset: Mapped[datetime | None] = mapped_column(UtcDateTime)
    moon_phase: Mapped[float | None] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(UtcDateTime)


class WeatherAlertModel(Base):
    __tablename__ = "weather_alerts"

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True
    )
    alert_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    sender_name: Mapped[str] = mapped_column(String(255))
    event: Mapped[str] = mapped_column(String(255))
    starts_at: Mapped[datetime] = mapped_column(UtcDateTime)
    ends_at: Mapped[datetime] = mapped_column(UtcDateTime)
    descriptions: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    tags: Mapped[list[str]] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(UtcDateTime)
