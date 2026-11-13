"""Transformação (T): JSON da OpenWeather → entidades de domínio.

Todas as conversões validam o formato e levantam ``PayloadError`` em caso de divergência,
de modo que dados malformados nunca chegam ao banco.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pyweather_etl.domain.entities import (
    CurrentSnapshot,
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    Location,
    WeatherAlert,
)
from pyweather_etl.domain.errors import InvalidCoordinatesError, PayloadError
from pyweather_etl.domain.value_objects import (
    AlertDescription,
    Coordinates,
    DailyFeelsLike,
    DailyTemperature,
    LocationSpec,
    Precipitation,
    TimezoneInfo,
    WeatherCondition,
    Wind,
)


Payload = Mapping[str, Any]


# --- Helpers primitivos ------------------------------------------------------------------------
def _as_mapping(value: Any, what: str) -> Payload:
    if not isinstance(value, Mapping):
        raise PayloadError(f"Esperado objeto JSON em '{what}', recebido {type(value).__name__}.")
    return value


def _require(record: Payload, key: str) -> Any:
    try:
        return record[key]
    except KeyError as exc:
        raise PayloadError(f"Campo obrigatório ausente: '{key}'.") from exc


def _to_float(value: Any, key: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise PayloadError(f"Valor numérico inválido em '{key}': {value!r}.") from exc


def _to_int(value: Any, key: str) -> int:
    try:
        return round(float(value))
    except (TypeError, ValueError, OverflowError) as exc:
        raise PayloadError(f"Valor inteiro inválido em '{key}': {value!r}.") from exc


def _to_datetime(value: Any, key: str) -> datetime:
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError) as exc:
        raise PayloadError(f"Timestamp Unix inválido em '{key}': {value!r}.") from exc


def _opt_float(record: Payload, key: str) -> float | None:
    value = record.get(key)
    return None if value is None else _to_float(value, key)


def _opt_int(record: Payload, key: str) -> int | None:
    value = record.get(key)
    return None if value is None else _to_int(value, key)


def _opt_datetime(record: Payload, key: str) -> datetime | None:
    value = record.get(key)
    return None if value is None else _to_datetime(value, key)


# --- Value objects -----------------------------------------------------------------------------
def map_condition(record: Payload) -> WeatherCondition | None:
    """Usa a primeira condição da lista ``weather`` (a principal)."""
    items = record.get("weather")
    if not items:
        return None
    first = _as_mapping(items[0], "weather[0]")
    return WeatherCondition(
        code=_to_int(_require(first, "id"), "weather.id"),
        main=str(first.get("main", "")),
        description=str(first.get("description", "")),
        icon=str(first.get("icon", "")),
    )


def map_wind(record: Payload) -> Wind:
    return Wind(
        speed=_opt_float(record, "wind_speed"),
        direction=_opt_int(record, "wind_deg"),
        gust=_opt_float(record, "wind_gust"),
    )


def _amount(value: Any, key: str) -> float | None:
    """Aceita ``{"1h": x}`` (formato documentado) ou um número simples (formato diário)."""
    if value is None:
        return None
    if isinstance(value, Mapping):
        inner = value.get("1h")
        return None if inner is None else _to_float(inner, f"{key}.1h")
    return _to_float(value, key)


def map_precipitation(record: Payload) -> Precipitation:
    return Precipitation(
        rain=_amount(record.get("rain"), "rain"),
        snow=_amount(record.get("snow"), "snow"),
        probability=_opt_float(record, "pop"),
    )


def map_timezone(payload: Payload) -> TimezoneInfo:
    return TimezoneInfo(
        name=str(_require(payload, "timezone")),
        offset_seconds=_to_int(_require(payload, "timezone_offset"), "timezone_offset"),
    )


# --- Condições atuais --------------------------------------------------------------------------
def _first_record(payload: Payload) -> Payload:
    data = _require(payload, "data")
    if not isinstance(data, list) or not data:
        raise PayloadError("A resposta não contém registros em 'data'.")
    return _as_mapping(data[0], "data[0]")


def map_current(record: Payload) -> CurrentWeather:
    return CurrentWeather(
        observed_at=_to_datetime(_require(record, "dt"), "dt"),
        temperature=_to_float(_require(record, "temp"), "temp"),
        feels_like=_to_float(_require(record, "feels_like"), "feels_like"),
        pressure=_to_int(_require(record, "pressure"), "pressure"),
        humidity=_to_int(_require(record, "humidity"), "humidity"),
        dew_point=_opt_float(record, "dew_point"),
        uvi=_opt_float(record, "uvi"),
        clouds=_opt_int(record, "clouds"),
        visibility=_opt_int(record, "visibility"),
        wind=map_wind(record),
        precipitation=map_precipitation(record),
        condition=map_condition(record),
        sunrise=_opt_datetime(record, "sunrise"),
        sunset=_opt_datetime(record, "sunset"),
    )


def map_current_snapshot(payload: Any) -> CurrentSnapshot:
    root = _as_mapping(payload, "resposta")
    record = _first_record(root)
    return CurrentSnapshot(
        weather=map_current(record),
        timezone=map_timezone(root),
        alert_ids=tuple(str(alert_id) for alert_id in record.get("alerts") or ()),
    )


# --- Linhas do tempo ---------------------------------------------------------------------------
def map_hourly(record: Payload) -> HourlyForecast:
    return HourlyForecast(
        forecast_at=_to_datetime(_require(record, "dt"), "dt"),
        temperature=_to_float(_require(record, "temp"), "temp"),
        feels_like=_to_float(_require(record, "feels_like"), "feels_like"),
        pressure=_to_int(_require(record, "pressure"), "pressure"),
        humidity=_to_int(_require(record, "humidity"), "humidity"),
        dew_point=_opt_float(record, "dew_point"),
        uvi=_opt_float(record, "uvi"),
        clouds=_opt_int(record, "clouds"),
        visibility=_opt_int(record, "visibility"),
        wind=map_wind(record),
        precipitation=map_precipitation(record),
        condition=map_condition(record),
    )


def _daily_temperature(record: Payload) -> DailyTemperature:
    temp = _as_mapping(_require(record, "temp"), "temp")
    return DailyTemperature(
        day=_opt_float(temp, "day"),
        min=_opt_float(temp, "min"),
        max=_opt_float(temp, "max"),
        night=_opt_float(temp, "night"),
        evening=_opt_float(temp, "eve"),
        morning=_opt_float(temp, "morn"),
    )


def _daily_feels_like(record: Payload) -> DailyFeelsLike:
    raw = record.get("feels_like")
    if not isinstance(raw, Mapping):
        return DailyFeelsLike()
    return DailyFeelsLike(
        day=_opt_float(raw, "day"),
        night=_opt_float(raw, "night"),
        evening=_opt_float(raw, "eve"),
        morning=_opt_float(raw, "morn"),
    )


def map_daily(record: Payload) -> DailyForecast:
    return DailyForecast(
        forecast_at=_to_datetime(_require(record, "dt"), "dt"),
        temperature=_daily_temperature(record),
        feels_like=_daily_feels_like(record),
        pressure=_opt_int(record, "pressure"),
        humidity=_opt_int(record, "humidity"),
        dew_point=_opt_float(record, "dew_point"),
        uvi=_opt_float(record, "uvi"),
        clouds=_opt_int(record, "clouds"),
        wind=map_wind(record),
        precipitation=map_precipitation(record),
        condition=map_condition(record),
        sunrise=_opt_datetime(record, "sunrise"),
        sunset=_opt_datetime(record, "sunset"),
        moonrise=_opt_datetime(record, "moonrise"),
        moonset=_opt_datetime(record, "moonset"),
        moon_phase=_opt_float(record, "moon_phase"),
    )


# --- Alertas e geocodificação ------------------------------------------------------------------
def map_alert(payload: Any) -> WeatherAlert:
    root = _as_mapping(payload, "alerta")
    descriptions = tuple(
        AlertDescription(
            language=str(_as_mapping(item, "description[]").get("language", "")),
            text=str(_as_mapping(item, "description[]").get("description", "")),
        )
        for item in root.get("description") or ()
    )
    return WeatherAlert(
        alert_id=str(_require(root, "id")),
        sender_name=str(root.get("sender_name", "")),
        event=str(root.get("event", "")),
        starts_at=_to_datetime(_require(root, "start"), "start"),
        ends_at=_to_datetime(_require(root, "end"), "end"),
        descriptions=descriptions,
        tags=tuple(str(tag) for tag in root.get("tags") or ()),
    )


def map_geocoding_item(item: Any, spec: LocationSpec) -> Location:
    root = _as_mapping(item, "geocoding[0]")
    try:
        coordinates = Coordinates(
            _to_float(_require(root, "lat"), "lat"),
            _to_float(_require(root, "lon"), "lon"),
        )
    except InvalidCoordinatesError as exc:
        raise PayloadError(str(exc)) from exc
    return Location(
        name=str(root.get("name") or spec.name),
        country=str(root.get("country") or spec.country),
        state=str(root["state"]) if root.get("state") else spec.state,
        coordinates=coordinates,
    )
