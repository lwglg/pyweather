"""Entidades do domínio climático."""

from dataclasses import dataclass, field
from datetime import datetime

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


@dataclass(frozen=True, slots=True)
class Location:
    """Local monitorado (cidade). ``id`` é atribuído na persistência."""

    name: str
    country: str
    coordinates: Coordinates
    state: str | None = None
    timezone: TimezoneInfo | None = None
    id: int | None = None


@dataclass(frozen=True, slots=True)
class CurrentWeather:
    """Observação das condições atuais de um local."""

    observed_at: datetime
    temperature: float
    feels_like: float
    pressure: int
    humidity: int
    dew_point: float | None = None
    uvi: float | None = None
    clouds: int | None = None
    visibility: int | None = None
    wind: Wind = field(default_factory=Wind)
    precipitation: Precipitation = field(default_factory=Precipitation)
    condition: WeatherCondition | None = None
    sunrise: datetime | None = None
    sunset: datetime | None = None


@dataclass(frozen=True, slots=True)
class HourlyForecast:
    """Previsão (ou histórico) com passo de uma hora."""

    forecast_at: datetime
    temperature: float
    feels_like: float
    pressure: int
    humidity: int
    dew_point: float | None = None
    uvi: float | None = None
    clouds: int | None = None
    visibility: int | None = None
    wind: Wind = field(default_factory=Wind)
    precipitation: Precipitation = field(default_factory=Precipitation)
    condition: WeatherCondition | None = None


@dataclass(frozen=True, slots=True)
class DailyForecast:
    """Previsão (ou histórico) com passo de um dia."""

    forecast_at: datetime
    temperature: DailyTemperature
    feels_like: DailyFeelsLike = field(default_factory=DailyFeelsLike)
    pressure: int | None = None
    humidity: int | None = None
    dew_point: float | None = None
    uvi: float | None = None
    clouds: int | None = None
    wind: Wind = field(default_factory=Wind)
    precipitation: Precipitation = field(default_factory=Precipitation)
    condition: WeatherCondition | None = None
    sunrise: datetime | None = None
    sunset: datetime | None = None
    moonrise: datetime | None = None
    moonset: datetime | None = None
    moon_phase: float | None = None


@dataclass(frozen=True, slots=True)
class WeatherAlert:
    """Alerta meteorológico emitido por uma agência nacional."""

    alert_id: str
    sender_name: str
    event: str
    starts_at: datetime
    ends_at: datetime
    descriptions: tuple[AlertDescription, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CurrentSnapshot:
    """Resultado da consulta de condições atuais: observação, fuso e alertas associados."""

    weather: CurrentWeather
    timezone: TimezoneInfo
    alert_ids: tuple[str, ...] = ()
