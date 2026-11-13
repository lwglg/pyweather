"""Tabelas (SQLModel) espelhando o esquema criado e mantido pelo ETL (via Alembic).

A API **não** cria nem altera o esquema: apenas lê. ``create_all`` é usado somente em testes.
"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


def _ts(*, primary_key: bool = False) -> Column[datetime]:
    return Column(DateTime(timezone=True), primary_key=primary_key)


class LocationTable(SQLModel, table=True):
    __tablename__ = "locations"

    id: int = Field(primary_key=True)
    name: str
    state: str | None = None
    country: str
    latitude: float
    longitude: float
    timezone: str | None = None
    timezone_offset: int | None = None
    created_at: datetime = Field(sa_column=_ts())
    updated_at: datetime = Field(sa_column=_ts())


class CurrentWeatherTable(SQLModel, table=True):
    __tablename__ = "current_weather"

    location_id: int = Field(foreign_key="locations.id", primary_key=True)
    observed_at: datetime = Field(sa_column=_ts(primary_key=True))
    temperature: float
    feels_like: float
    pressure: int
    humidity: int
    dew_point: float | None = None
    uvi: float | None = None
    clouds: int | None = None
    visibility: int | None = None
    rain_1h: float | None = None
    snow_1h: float | None = None
    wind_speed: float | None = None
    wind_deg: int | None = None
    wind_gust: float | None = None
    condition_code: int | None = None
    condition_main: str | None = None
    condition_description: str | None = None
    condition_icon: str | None = None
    sunrise: datetime | None = Field(default=None, sa_column=_ts())
    sunset: datetime | None = Field(default=None, sa_column=_ts())
    fetched_at: datetime = Field(sa_column=_ts())


class HourlyForecastTable(SQLModel, table=True):
    __tablename__ = "hourly_forecasts"

    location_id: int = Field(foreign_key="locations.id", primary_key=True)
    forecast_at: datetime = Field(sa_column=_ts(primary_key=True))
    temperature: float
    feels_like: float
    pressure: int
    humidity: int
    dew_point: float | None = None
    uvi: float | None = None
    clouds: int | None = None
    visibility: int | None = None
    rain_1h: float | None = None
    snow_1h: float | None = None
    wind_speed: float | None = None
    wind_deg: int | None = None
    wind_gust: float | None = None
    pop: float | None = None
    condition_code: int | None = None
    condition_main: str | None = None
    condition_description: str | None = None
    condition_icon: str | None = None
    fetched_at: datetime = Field(sa_column=_ts())


class DailyForecastTable(SQLModel, table=True):
    __tablename__ = "daily_forecasts"

    location_id: int = Field(foreign_key="locations.id", primary_key=True)
    forecast_at: datetime = Field(sa_column=_ts(primary_key=True))
    temp_day: float | None = None
    temp_min: float | None = None
    temp_max: float | None = None
    temp_night: float | None = None
    temp_eve: float | None = None
    temp_morn: float | None = None
    feels_like_day: float | None = None
    feels_like_night: float | None = None
    feels_like_eve: float | None = None
    feels_like_morn: float | None = None
    pressure: int | None = None
    humidity: int | None = None
    dew_point: float | None = None
    uvi: float | None = None
    clouds: int | None = None
    wind_speed: float | None = None
    wind_deg: int | None = None
    wind_gust: float | None = None
    rain: float | None = None
    snow: float | None = None
    pop: float | None = None
    condition_code: int | None = None
    condition_main: str | None = None
    condition_description: str | None = None
    condition_icon: str | None = None
    sunrise: datetime | None = Field(default=None, sa_column=_ts())
    sunset: datetime | None = Field(default=None, sa_column=_ts())
    moonrise: datetime | None = Field(default=None, sa_column=_ts())
    moonset: datetime | None = Field(default=None, sa_column=_ts())
    moon_phase: float | None = None
    fetched_at: datetime = Field(sa_column=_ts())


class WeatherAlertTable(SQLModel, table=True):
    __tablename__ = "weather_alerts"

    location_id: int = Field(foreign_key="locations.id", primary_key=True)
    alert_id: str = Field(primary_key=True)
    sender_name: str
    event: str
    starts_at: datetime = Field(sa_column=_ts())
    ends_at: datetime = Field(sa_column=_ts())
    descriptions: list[dict[str, str]] = Field(sa_column=Column(JSON, nullable=False))
    tags: list[str] = Field(sa_column=Column(JSON, nullable=False))
    fetched_at: datetime = Field(sa_column=_ts())
