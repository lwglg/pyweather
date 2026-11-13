from datetime import UTC, datetime
from typing import Any

import pytest

from pyweather_etl.domain.errors import PayloadError
from pyweather_etl.domain.value_objects import LocationSpec
from pyweather_etl.infrastructure.openweather import mappers


def test_current_snapshot_completo(current_payload: dict[str, Any]) -> None:
    snapshot = mappers.map_current_snapshot(current_payload)

    weather = snapshot.weather
    assert weather.observed_at == datetime.fromtimestamp(1_777_449_371, tz=UTC)
    assert weather.temperature == 24.5
    assert weather.humidity == 70
    assert weather.wind.speed == 4.2
    assert weather.wind.direction == 120
    assert weather.wind.gust == 7.1
    assert weather.precipitation.rain == 0.4
    assert weather.precipitation.snow is None
    assert weather.condition is not None
    assert weather.condition.code == 500
    assert weather.condition.description == "chuva leve"
    assert weather.sunrise is not None
    assert snapshot.timezone.name == "America/Sao_Paulo"
    assert snapshot.timezone.offset_seconds == -10800
    assert snapshot.alert_ids == ("ALERT-1", "ALERT-2")


def test_current_sem_campos_opcionais(current_payload: dict[str, Any]) -> None:
    record = current_payload["data"][0]
    for key in ("dew_point", "uvi", "weather", "alerts", "rain", "wind_gust", "sunrise"):
        record.pop(key)

    snapshot = mappers.map_current_snapshot(current_payload)

    assert snapshot.weather.condition is None
    assert snapshot.weather.dew_point is None
    assert snapshot.weather.sunrise is None
    assert snapshot.alert_ids == ()


@pytest.mark.parametrize("missing", ["dt", "temp", "feels_like", "pressure", "humidity"])
def test_current_campo_obrigatorio_ausente(current_payload: dict[str, Any], missing: str) -> None:
    current_payload["data"][0].pop(missing)
    with pytest.raises(PayloadError, match=missing):
        mappers.map_current_snapshot(current_payload)


@pytest.mark.parametrize(
    "payload",
    [[], "texto", {"timezone": "UTC", "timezone_offset": 0, "data": []}],
)
def test_current_payload_invalido(payload: Any) -> None:
    with pytest.raises(PayloadError):
        mappers.map_current_snapshot(payload)


def test_valor_numerico_invalido(current_payload: dict[str, Any]) -> None:
    current_payload["data"][0]["temp"] = "quente"
    with pytest.raises(PayloadError, match="temp"):
        mappers.map_current_snapshot(current_payload)


def test_timestamp_invalido(current_payload: dict[str, Any]) -> None:
    current_payload["data"][0]["dt"] = "ontem"
    with pytest.raises(PayloadError, match="dt"):
        mappers.map_current_snapshot(current_payload)


def test_hourly(hourly_record: dict[str, Any]) -> None:
    forecast = mappers.map_hourly(hourly_record)

    assert forecast.forecast_at == datetime.fromtimestamp(1_777_453_200, tz=UTC)
    assert forecast.precipitation.probability == 0.35
    assert forecast.precipitation.rain == 0.2
    assert forecast.condition is not None
    assert forecast.condition.main == "Clouds"
    assert forecast.visibility == 9000


def test_daily_com_chuva_como_numero(daily_record: dict[str, Any]) -> None:
    forecast = mappers.map_daily(daily_record)

    assert forecast.temperature.min == 20.1
    assert forecast.temperature.max == 28.3
    assert forecast.temperature.evening == 25.0
    assert forecast.feels_like.morning == 21.2
    assert forecast.precipitation.rain == 1.5
    assert forecast.moon_phase == 0.43
    assert forecast.moonrise is not None


def test_daily_chuva_no_formato_documentado(daily_record: dict[str, Any]) -> None:
    daily_record["rain"] = {"1h": 2.5}
    daily_record["snow"] = {"1h": 0.1}
    forecast = mappers.map_daily(daily_record)
    assert forecast.precipitation.rain == 2.5
    assert forecast.precipitation.snow == 0.1


def test_daily_sem_sensacao_termica(daily_record: dict[str, Any]) -> None:
    daily_record.pop("feels_like")
    forecast = mappers.map_daily(daily_record)
    assert forecast.feels_like.day is None


def test_daily_temp_deve_ser_objeto(daily_record: dict[str, Any]) -> None:
    daily_record["temp"] = 25.0
    with pytest.raises(PayloadError, match="temp"):
        mappers.map_daily(daily_record)


def test_condicao_invalida() -> None:
    with pytest.raises(PayloadError):
        mappers.map_condition({"weather": ["não é objeto"]})
    with pytest.raises(PayloadError, match=r"weather\.id"):
        mappers.map_condition({"weather": [{"id": "x"}]})


def test_alert(alert_payload: dict[str, Any]) -> None:
    alert = mappers.map_alert(alert_payload)

    assert alert.alert_id == "ALERT-1"
    assert alert.sender_name == "INMET"
    assert alert.starts_at < alert.ends_at
    assert [d.language for d in alert.descriptions] == ["pt-BR", "en-GB"]
    assert alert.tags == ("Thunderstorm", "Rain")


def test_alert_minimo() -> None:
    alert = mappers.map_alert({"id": "X", "start": 1, "end": 2})
    assert alert.descriptions == ()
    assert alert.tags == ()
    assert alert.event == ""


def test_alert_sem_id() -> None:
    with pytest.raises(PayloadError, match="id"):
        mappers.map_alert({"start": 1, "end": 2})


def test_geocoding(geocoding_payload: list[dict[str, Any]]) -> None:
    spec = LocationSpec(name="Floripa", country="BR")
    location = mappers.map_geocoding_item(geocoding_payload[0], spec)

    assert location.name == "Florianópolis"
    assert location.state == "Santa Catarina"
    assert location.coordinates.latitude == -27.5954
    assert location.id is None


def test_geocoding_usa_valores_da_especificacao_quando_ausentes() -> None:
    spec = LocationSpec(name="Cidade", country="BR", state="SC")
    location = mappers.map_geocoding_item({"lat": 1.0, "lon": 2.0}, spec)
    assert (location.name, location.country, location.state) == ("Cidade", "BR", "SC")


def test_geocoding_coordenadas_invalidas() -> None:
    spec = LocationSpec(name="X", country="BR")
    with pytest.raises(PayloadError, match="Latitude"):
        mappers.map_geocoding_item({"lat": 120.0, "lon": 0.0}, spec)
