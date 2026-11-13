"""Modelos de leitura do domínio (imutáveis). A API apenas consulta; a escrita é do ETL."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class Location:
    id: int
    name: str
    state: str | None
    country: str
    latitude: float
    longitude: float
    timezone: str | None
    timezone_offset: int | None


@dataclass(frozen=True, slots=True)
class Condition:
    code: int | None
    main: str | None
    description: str | None
    icon: str | None


@dataclass(frozen=True, slots=True)
class CurrentWeather:
    location_id: int
    observed_at: datetime
    temperature: float
    feels_like: float
    pressure: int
    humidity: int
    dew_point: float | None
    uvi: float | None
    clouds: int | None
    visibility: int | None
    wind_speed: float | None
    wind_deg: int | None
    wind_gust: float | None
    rain_1h: float | None
    snow_1h: float | None
    condition: Condition
    sunrise: datetime | None
    sunset: datetime | None
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class HourlyForecast:
    location_id: int
    forecast_at: datetime
    temperature: float
    feels_like: float
    pressure: int
    humidity: int
    dew_point: float | None
    uvi: float | None
    clouds: int | None
    visibility: int | None
    wind_speed: float | None
    wind_deg: int | None
    wind_gust: float | None
    rain_1h: float | None
    snow_1h: float | None
    pop: float | None
    condition: Condition
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class DailyForecast:
    location_id: int
    forecast_at: datetime
    temp_day: float | None
    temp_min: float | None
    temp_max: float | None
    temp_night: float | None
    temp_eve: float | None
    temp_morn: float | None
    feels_like_day: float | None
    feels_like_night: float | None
    feels_like_eve: float | None
    feels_like_morn: float | None
    pressure: int | None
    humidity: int | None
    dew_point: float | None
    uvi: float | None
    clouds: int | None
    wind_speed: float | None
    wind_deg: int | None
    wind_gust: float | None
    rain: float | None
    snow: float | None
    pop: float | None
    condition: Condition
    sunrise: datetime | None
    sunset: datetime | None
    moonrise: datetime | None
    moonset: datetime | None
    moon_phase: float | None
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class AlertDescription:
    language: str
    description: str


@dataclass(frozen=True, slots=True)
class WeatherAlert:
    location_id: int
    alert_id: str
    sender_name: str
    event: str
    starts_at: datetime
    ends_at: datetime
    descriptions: tuple[AlertDescription, ...]
    tags: tuple[str, ...]
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class Page[T]:
    """Página de resultados com o total de itens que satisfazem o filtro."""

    items: tuple[T, ...]
    total: int
    limit: int
    offset: int


# --- Filtros -----------------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Pagination:
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class LocationFilter:
    name: str | None = None
    state: str | None = None
    country: str | None = None


@dataclass(frozen=True, slots=True)
class TimeRange:
    """Intervalo de tempo [start, end] (ambos inclusivos e opcionais)."""

    start: datetime | None = None
    end: datetime | None = None


@dataclass(frozen=True, slots=True)
class CurrentFilter:
    period: TimeRange = TimeRange()
    min_temperature: float | None = None
    max_temperature: float | None = None
    min_humidity: int | None = None
    max_humidity: int | None = None
    condition: str | None = None
    order: SortOrder = SortOrder.DESC


@dataclass(frozen=True, slots=True)
class HourlyFilter:
    period: TimeRange = TimeRange()
    min_temperature: float | None = None
    max_temperature: float | None = None
    min_pop: float | None = None
    condition: str | None = None
    order: SortOrder = SortOrder.ASC


@dataclass(frozen=True, slots=True)
class DailyFilter:
    period: TimeRange = TimeRange()
    min_temperature: float | None = None  # sobre a mínima do dia
    max_temperature: float | None = None  # sobre a máxima do dia
    min_pop: float | None = None
    condition: str | None = None
    order: SortOrder = SortOrder.ASC


@dataclass(frozen=True, slots=True)
class AlertFilter:
    event: str | None = None
    sender: str | None = None
    active_at: datetime | None = None
    order: SortOrder = SortOrder.DESC
