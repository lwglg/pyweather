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
    assert weather.feels_like == 25.1
    assert weather.pressure == 1018
    assert weather.humidity == 70
    assert weather.clouds == 40
    assert weather.visibility == 10000
    assert weather.wind.speed == 4.2
    assert weather.wind.direction == 120
    assert weather.wind.gust == 7.1
    assert weather.precipitation.rain == 0.4
    assert weather.precipitation.snow is None
    assert weather.precipitation.probability is None
    assert weather.dew_point is None
    assert weather.uvi is None
    assert weather.condition is not None
    assert weather.condition.code == 500
    assert weather.condition.description == "chuva leve"
    assert weather.sunrise == datetime.fromtimestamp(1_777_437_375, tz=UTC)
    assert snapshot.timezone.name == "UTC-03:00"
    assert snapshot.timezone.offset_seconds == -10800


def test_current_sem_campos_opcionais(current_payload: dict[str, Any]) -> None:
    for key in ("weather", "rain", "wind", "clouds", "sys", "visibility"):
        current_payload.pop(key)

    weather = mappers.map_current_snapshot(current_payload).weather

    assert weather.condition is None
    assert weather.wind.speed is None
    assert weather.precipitation.rain is None
    assert weather.clouds is None
    assert weather.sunrise is None


@pytest.mark.parametrize("missing", ["dt", "main", "timezone"])
def test_current_campo_obrigatorio_ausente(current_payload: dict[str, Any], missing: str) -> None:
    current_payload.pop(missing)
    with pytest.raises(PayloadError, match=missing):
        mappers.map_current_snapshot(current_payload)


@pytest.mark.parametrize("missing", ["temp", "feels_like", "pressure", "humidity"])
def test_current_campo_principal_ausente(current_payload: dict[str, Any], missing: str) -> None:
    current_payload["main"].pop(missing)
    with pytest.raises(PayloadError, match=missing):
        mappers.map_current_snapshot(current_payload)


@pytest.mark.parametrize("payload", [[], "texto", {"timezone": 0, "main": "x", "dt": 1}])
def test_current_payload_invalido(payload: Any) -> None:
    with pytest.raises(PayloadError):
        mappers.map_current_snapshot(payload)


def test_valor_numerico_invalido(current_payload: dict[str, Any]) -> None:
    current_payload["main"]["temp"] = "quente"
    with pytest.raises(PayloadError, match="temp"):
        mappers.map_current_snapshot(current_payload)


def test_timestamp_invalido(current_payload: dict[str, Any]) -> None:
    current_payload["dt"] = "ontem"
    with pytest.raises(PayloadError, match="dt"):
        mappers.map_current_snapshot(current_payload)


def test_vento_e_chuva_devem_ser_objetos(current_payload: dict[str, Any]) -> None:
    current_payload["wind"] = 4.2
    with pytest.raises(PayloadError, match="wind"):
        mappers.map_current_snapshot(current_payload)


@pytest.mark.parametrize(
    ("offset", "name"),
    [(-10800, "UTC-03:00"), (0, "UTC+00:00"), (19800, "UTC+05:30"), (-12600, "UTC-03:30")],
)
def test_nome_do_fuso_derivado_do_deslocamento(offset: int, name: str) -> None:
    timezone = mappers.timezone_from_offset(offset)
    assert (timezone.name, timezone.offset_seconds) == (name, offset)


def test_forecast_passos(forecast_payload: dict[str, Any]) -> None:
    forecast = mappers.map_forecast(forecast_payload)

    assert len(forecast.steps) == 4
    first = forecast.steps[0]
    assert first.forecast_at == datetime(2026, 11, 12, 15, 0, tzinfo=UTC)
    assert first.temperature == 24.0
    assert first.precipitation.probability == 0.35
    assert first.precipitation.rain == 0.5
    assert first.clouds == 60
    assert first.visibility == 9000
    assert first.condition is not None
    assert first.condition.main == "Clouds"
    assert [step.forecast_at for step in forecast.steps] == sorted(
        step.forecast_at for step in forecast.steps
    )


def test_forecast_resumo_diario_por_dia_civil_local(forecast_payload: dict[str, Any]) -> None:
    daily = mappers.map_forecast(forecast_payload).daily

    assert len(daily) == 2
    day1, day2 = daily
    # O dia civil local (UTC-3) começa às 03:00 UTC.
    assert day1.forecast_at == datetime(2026, 11, 12, 3, 0, tzinfo=UTC)
    assert day2.forecast_at == datetime(2026, 11, 13, 3, 0, tzinfo=UTC)

    assert day1.temperature.min == 23.0
    assert day1.temperature.max == 29.5
    assert day1.temperature.day == 26.0
    assert day1.temperature.night is None
    assert day1.feels_like.day == 26.8
    assert day1.pressure == 1016
    assert day1.humidity == 65
    assert day1.clouds == 60
    assert day1.wind.speed == 5.5
    assert day1.wind.direction == 90
    assert day1.wind.gust == 9.0
    assert day1.precipitation.rain == 1.75
    assert day1.precipitation.probability == 0.8
    assert day1.condition is not None
    assert day1.condition.code == 803


def test_forecast_resumo_diario_com_dados_ausentes(forecast_payload: dict[str, Any]) -> None:
    day2 = mappers.map_forecast(forecast_payload).daily[1]

    assert day2.precipitation.rain == 0.25
    assert day2.precipitation.snow is None
    assert day2.precipitation.probability == 0.2
    assert day2.wind.speed == 3.8
    assert day2.condition is not None
    assert day2.condition.code == 500


def test_forecast_sem_clima_nem_vento_nem_chuva(forecast_payload: dict[str, Any]) -> None:
    for item in forecast_payload["list"]:
        for key in ("weather", "wind", "rain", "clouds", "pop"):
            item.pop(key, None)

    daily = mappers.map_forecast(forecast_payload).daily

    assert daily[0].condition is None
    assert daily[0].wind.speed is None
    assert daily[0].wind.gust is None
    assert daily[0].precipitation.rain is None
    assert daily[0].precipitation.probability is None
    assert daily[0].clouds is None


def test_forecast_usa_temp_quando_faltam_minima_e_maxima(forecast_payload: dict[str, Any]) -> None:
    for item in forecast_payload["list"]:
        item["main"].pop("temp_min")
        item["main"].pop("temp_max")

    day1 = mappers.map_forecast(forecast_payload).daily[0]
    assert (day1.temperature.min, day1.temperature.max) == (24.0, 28.0)


def test_forecast_remove_passos_duplicados_e_ordena(forecast_payload: dict[str, Any]) -> None:
    forecast_payload["list"].append(forecast_payload["list"][0])
    forecast_payload["list"].reverse()

    forecast = mappers.map_forecast(forecast_payload)

    assert len(forecast.steps) == 4
    assert forecast.steps[0].forecast_at < forecast.steps[-1].forecast_at


def test_forecast_lista_vazia() -> None:
    forecast = mappers.map_forecast({"list": [], "city": {"timezone": 0}})
    assert forecast.steps == ()
    assert forecast.daily == ()


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"city": {"timezone": 0}},
        {"list": "x", "city": {"timezone": 0}},
        {"list": ["x"], "city": {"timezone": 0}},
        {"list": []},
        {"list": [], "city": {}},
    ],
)
def test_forecast_payload_invalido(payload: Any) -> None:
    with pytest.raises(PayloadError):
        mappers.map_forecast(payload)


def test_chuva_e_neve_aceitam_janelas_de_1h_ou_3h() -> None:
    assert mappers.map_precipitation({"rain": {"1h": 2.5}}).rain == 2.5
    assert mappers.map_precipitation({"snow": {"3h": 0.1}}).snow == 0.1
    assert mappers.map_precipitation({"rain": {}}).rain is None


def test_condicao_invalida() -> None:
    with pytest.raises(PayloadError):
        mappers.map_condition({"weather": ["não é objeto"]})
    with pytest.raises(PayloadError, match=r"weather\.id"):
        mappers.map_condition({"weather": [{"id": "x"}]})


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
