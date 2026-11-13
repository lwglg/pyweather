"""Transformação (T): JSON da OpenWeather (plano gratuito) → entidades de domínio.

Formatos tratados: Current Weather Data 2.5 e 5 Day / 3 Hour Forecast 2.5.

Todas as conversões validam o formato e levantam ``PayloadError`` em caso de divergência,
de modo que dados malformados nunca chegam ao banco.
"""

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from statistics import fmean
from typing import Any

from pyweather_etl.domain.entities import (
    CurrentSnapshot,
    CurrentWeather,
    DailyForecast,
    Forecast,
    HourlyForecast,
    Location,
)
from pyweather_etl.domain.errors import InvalidCoordinatesError, PayloadError
from pyweather_etl.domain.value_objects import (
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
    raw = record.get("wind")
    if raw is None:
        return Wind()
    wind = _as_mapping(raw, "wind")
    return Wind(
        speed=_opt_float(wind, "speed"),
        direction=_opt_int(wind, "deg"),
        gust=_opt_float(wind, "gust"),
    )


def _amount(record: Payload, key: str) -> float | None:
    """Volume (mm) de ``rain``/``snow``: ``{"1h": x}`` (atual) ou ``{"3h": x}`` (previsão)."""
    raw = record.get(key)
    if raw is None:
        return None
    volume = _as_mapping(raw, key)
    for window in ("1h", "3h"):
        if volume.get(window) is not None:
            return _to_float(volume[window], f"{key}.{window}")
    return None


def map_precipitation(record: Payload) -> Precipitation:
    return Precipitation(
        rain=_amount(record, "rain"),
        snow=_amount(record, "snow"),
        probability=_opt_float(record, "pop"),
    )


def _main(record: Payload) -> Payload:
    return _as_mapping(_require(record, "main"), "main")


def _clouds(record: Payload) -> int | None:
    raw = record.get("clouds")
    return None if raw is None else _opt_int(_as_mapping(raw, "clouds"), "all")


def timezone_from_offset(offset_seconds: int) -> TimezoneInfo:
    """O plano gratuito informa apenas o deslocamento; o nome é derivado (ex.: ``UTC-03:00``)."""
    sign = "-" if offset_seconds < 0 else "+"
    hours, remainder = divmod(abs(offset_seconds), 3600)
    return TimezoneInfo(
        name=f"UTC{sign}{hours:02d}:{remainder // 60:02d}", offset_seconds=offset_seconds
    )


# --- Condições atuais --------------------------------------------------------------------------
def map_current(record: Payload) -> CurrentWeather:
    main = _main(record)
    sys_info = record.get("sys")
    sun = _as_mapping(sys_info, "sys") if sys_info is not None else {}
    return CurrentWeather(
        observed_at=_to_datetime(_require(record, "dt"), "dt"),
        temperature=_to_float(_require(main, "temp"), "main.temp"),
        feels_like=_to_float(_require(main, "feels_like"), "main.feels_like"),
        pressure=_to_int(_require(main, "pressure"), "main.pressure"),
        humidity=_to_int(_require(main, "humidity"), "main.humidity"),
        clouds=_clouds(record),
        visibility=_opt_int(record, "visibility"),
        wind=map_wind(record),
        precipitation=map_precipitation(record),
        condition=map_condition(record),
        sunrise=_opt_datetime(sun, "sunrise"),
        sunset=_opt_datetime(sun, "sunset"),
    )


def map_current_snapshot(payload: Any) -> CurrentSnapshot:
    root = _as_mapping(payload, "resposta")
    offset = _to_int(_require(root, "timezone"), "timezone")
    return CurrentSnapshot(weather=map_current(root), timezone=timezone_from_offset(offset))


# --- Previsão (passos de 3 h) e resumo diário --------------------------------------------------
def map_step(record: Payload) -> HourlyForecast:
    main = _main(record)
    return HourlyForecast(
        forecast_at=_to_datetime(_require(record, "dt"), "dt"),
        temperature=_to_float(_require(main, "temp"), "main.temp"),
        feels_like=_to_float(_require(main, "feels_like"), "main.feels_like"),
        pressure=_to_int(_require(main, "pressure"), "main.pressure"),
        humidity=_to_int(_require(main, "humidity"), "main.humidity"),
        clouds=_clouds(record),
        visibility=_opt_int(record, "visibility"),
        wind=map_wind(record),
        precipitation=map_precipitation(record),
        condition=map_condition(record),
    )


def _mean(values: Sequence[float]) -> float | None:
    return round(fmean(values), 2) if values else None


def _mean_int(values: Sequence[float]) -> int | None:
    return round(fmean(values)) if values else None


def _total(values: Sequence[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return round(sum(present), 2) if present else None


def _present(values: Sequence[float | None]) -> list[float]:
    return [value for value in values if value is not None]


def _daily_summary(
    day: date, offset: timedelta, entries: Sequence[tuple[Payload, HourlyForecast]]
) -> DailyForecast:
    """Resume os passos de um dia civil local em um ``DailyForecast``."""
    steps = [step for _, step in entries]
    mins = [
        _to_float(_main(raw).get("temp_min", step.temperature), "main.temp_min")
        for raw, step in entries
    ]
    maxs = [
        _to_float(_main(raw).get("temp_max", step.temperature), "main.temp_max")
        for raw, step in entries
    ]
    strongest = max(steps, key=lambda step: step.wind.speed or 0.0)
    conditions = Counter(step.condition.code for step in steps if step.condition)
    top_code = conditions.most_common(1)[0][0] if conditions else None
    condition = next(
        (step.condition for step in steps if step.condition and step.condition.code == top_code),
        None,
    )
    local_midnight = datetime(day.year, day.month, day.day, tzinfo=UTC) - offset
    return DailyForecast(
        forecast_at=local_midnight,
        temperature=DailyTemperature(
            day=_mean([step.temperature for step in steps]),
            min=min(mins),
            max=max(maxs),
        ),
        feels_like=DailyFeelsLike(day=_mean([step.feels_like for step in steps])),
        pressure=_mean_int([step.pressure for step in steps]),
        humidity=_mean_int([step.humidity for step in steps]),
        clouds=_mean_int(_present([step.clouds for step in steps])),
        wind=Wind(
            speed=strongest.wind.speed,
            direction=strongest.wind.direction,
            gust=max(_present([step.wind.gust for step in steps]), default=None),
        ),
        precipitation=Precipitation(
            rain=_total([step.precipitation.rain for step in steps]),
            snow=_total([step.precipitation.snow for step in steps]),
            probability=max(
                _present([step.precipitation.probability for step in steps]), default=None
            ),
        ),
        condition=condition,
    )


def map_forecast(payload: Any) -> Forecast:
    """Converte a resposta de ``/data/2.5/forecast`` em passos de 3 h + resumo diário.

    Os dias são os **civis do local** (usa ``city.timezone``). O primeiro e o último podem ser
    parciais, pois a janela de 5 dias não começa à meia-noite.
    """
    root = _as_mapping(payload, "resposta")
    items = _require(root, "list")
    if not isinstance(items, list):
        raise PayloadError("O campo 'list' da previsão não é uma lista.")
    city = _as_mapping(_require(root, "city"), "city")
    offset = timedelta(seconds=_to_int(_require(city, "timezone"), "city.timezone"))

    entries: list[tuple[Payload, HourlyForecast]] = []
    for item in items:
        raw = _as_mapping(item, "list[]")
        entries.append((raw, map_step(raw)))
    unique = {step.forecast_at: (raw, step) for raw, step in entries}
    ordered = sorted(unique.values(), key=lambda pair: pair[1].forecast_at)

    by_day: dict[date, list[tuple[Payload, HourlyForecast]]] = defaultdict(list)
    for raw, step in ordered:
        by_day[(step.forecast_at + offset).date()].append((raw, step))
    daily = tuple(_daily_summary(day, offset, group) for day, group in sorted(by_day.items()))
    return Forecast(steps=tuple(step for _, step in ordered), daily=daily)


# --- Geocodificação ----------------------------------------------------------------------------
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
