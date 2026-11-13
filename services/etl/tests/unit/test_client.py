from collections.abc import Callable
from typing import Any

import httpx
import pytest

from pyweather_etl.domain.errors import (
    AuthenticationError,
    ConfigurationError,
    LocationNotFoundError,
    PayloadError,
    ProviderUnavailableError,
    RateLimitError,
    ResourceNotFoundError,
    WeatherProviderError,
)
from pyweather_etl.domain.value_objects import Coordinates, LocationSpec
from pyweather_etl.infrastructure.openweather.client import OpenWeatherClient


BASE = "https://api.test"
COORDS = Coordinates(-27.59, -48.54)

Handler = Callable[[httpx.Request], httpx.Response]


def make_client(
    handler: Handler, *, retries: int = 2, sleeps: list[float] | None = None
) -> OpenWeatherClient:
    http = httpx.Client(base_url=BASE, transport=httpx.MockTransport(handler))
    recorded = sleeps if sleeps is not None else []
    return OpenWeatherClient(
        "chave-secreta",
        base_url=BASE,
        client=http,
        max_retries=retries,
        backoff_seconds=0.5,
        sleep=recorded.append,
    )


def test_sem_chave_levanta_erro_de_configuracao() -> None:
    with pytest.raises(ConfigurationError):
        OpenWeatherClient("")


def test_fetch_current_envia_parametros_e_mapeia(current_payload: dict[str, Any]) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=current_payload)

    snapshot = make_client(handler).fetch_current(COORDS)

    request = seen[0]
    assert request.url.path == "/data/4.0/onecall/current"
    assert request.url.params["lat"] == "-27.59"
    assert request.url.params["units"] == "metric"
    assert request.url.params["lang"] == "pt_br"
    assert request.url.params["appid"] == "chave-secreta"
    assert snapshot.weather.temperature == 24.5


def test_locate_usa_geocodificacao(geocoding_payload: list[dict[str, Any]]) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=geocoding_payload)

    location = make_client(handler).locate(LocationSpec("Florianópolis", "BR", "Santa Catarina"))

    assert seen[0].url.path == "/geo/1.0/direct"
    assert seen[0].url.params["q"] == "Florianópolis,BR"
    assert seen[0].url.params["limit"] == "1"
    assert location.coordinates.latitude == -27.5954


def test_locate_inclui_estado_apenas_nos_eua(geocoding_payload: list[dict[str, Any]]) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=geocoding_payload)

    make_client(handler).locate(LocationSpec("Austin", "US", "TX"))
    assert seen[0].url.params["q"] == "Austin,TX,US"


def test_locate_cidade_inexistente() -> None:
    client = make_client(lambda _: httpx.Response(200, json=[]))
    with pytest.raises(LocationNotFoundError):
        client.locate(LocationSpec("Nárnia", "BR"))


def test_fetch_hourly_segue_paginacao_e_remove_duplicados(
    hourly_record: dict[str, Any],
) -> None:
    second = {**hourly_record, "dt": hourly_record["dt"] + 3600}
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if "start" in request.url.params:
            return httpx.Response(200, json={"data": [hourly_record, second]})
        next_url = (
            f"{BASE}/data/4.0/onecall/timeline/1h?lat=-27.59&lon=-48.54&start=999&appid=OUTRA"
        )
        return httpx.Response(200, json={"data": [hourly_record], "next": next_url})

    forecasts = make_client(handler).fetch_hourly(COORDS, pages=3)

    assert [f.forecast_at.timestamp() for f in forecasts] == [
        hourly_record["dt"],
        second["dt"],
    ]
    assert len(calls) == 2
    # A chave configurada substitui qualquer appid embutido na URL de paginação.
    assert calls[1].url.params["appid"] == "chave-secreta"
    assert calls[1].url.params["units"] == "metric"


def test_fetch_hourly_respeita_limite_de_paginas(hourly_record: dict[str, Any]) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        next_url = f"{BASE}/data/4.0/onecall/timeline/1h?lat=1&lon=2&start=1"
        return httpx.Response(200, json={"data": [hourly_record], "next": next_url})

    make_client(handler).fetch_hourly(COORDS, pages=1)
    assert len(calls) == 1


def test_fetch_hourly_zero_paginas_nao_chama_api() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("não deveria chamar a API")

    assert make_client(handler).fetch_hourly(COORDS, pages=0) == []


def test_paginacao_ignora_host_inesperado(hourly_record: dict[str, Any]) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200, json={"data": [hourly_record], "next": "https://evil.example/steal?x=1"}
        )

    forecasts = make_client(handler).fetch_hourly(COORDS, pages=3)
    assert len(forecasts) == 1
    assert len(calls) == 1


def test_fetch_daily(daily_record: dict[str, Any]) -> None:
    client = make_client(lambda _: httpx.Response(200, json={"data": [daily_record]}))
    forecasts = client.fetch_daily(COORDS, pages=1)
    assert len(forecasts) == 1
    assert forecasts[0].temperature.max == 28.3


@pytest.mark.parametrize("payload", [{"foo": 1}, {"data": "x"}, {"data": ["x"]}, []])
def test_timeline_payload_invalido(payload: Any) -> None:
    client = make_client(lambda _: httpx.Response(200, json=payload))
    with pytest.raises(PayloadError):
        client.fetch_daily(COORDS, pages=1)


def test_fetch_alerts_ignora_inexistentes_e_deduplica(alert_payload: dict[str, Any]) -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("MISSING"):
            return httpx.Response(404, json={"message": "not found"})
        return httpx.Response(200, json=alert_payload)

    alerts = make_client(handler).fetch_alerts(["ALERT-1", "ALERT-1", "MISSING"])

    assert [a.alert_id for a in alerts] == ["ALERT-1"]
    assert paths == [
        "/data/4.0/onecall/alert/ALERT-1",
        "/data/4.0/onecall/alert/MISSING",
    ]


def test_retry_em_5xx_com_backoff_exponencial(current_payload: dict[str, Any]) -> None:
    responses = iter(
        [httpx.Response(503), httpx.Response(502), httpx.Response(200, json=current_payload)]
    )
    sleeps: list[float] = []

    snapshot = make_client(lambda _: next(responses), retries=3, sleeps=sleeps).fetch_current(
        COORDS
    )

    assert snapshot.weather.temperature == 24.5
    assert sleeps == [0.5, 1.0]


def test_429_respeita_retry_after(current_payload: dict[str, Any]) -> None:
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "7"}),
            httpx.Response(200, json=current_payload),
        ]
    )
    sleeps: list[float] = []

    make_client(lambda _: next(responses), sleeps=sleeps).fetch_current(COORDS)
    assert sleeps == [7.0]


def test_retry_after_invalido_usa_backoff(current_payload: dict[str, Any]) -> None:
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "breve"}),
            httpx.Response(200, json=current_payload),
        ]
    )
    sleeps: list[float] = []

    make_client(lambda _: next(responses), sleeps=sleeps).fetch_current(COORDS)
    assert sleeps == [0.5]


def test_rate_limit_esgotado() -> None:
    sleeps: list[float] = []
    client = make_client(lambda _: httpx.Response(429), retries=2, sleeps=sleeps)
    with pytest.raises(RateLimitError):
        client.fetch_current(COORDS)
    assert len(sleeps) == 2


def test_5xx_esgotado() -> None:
    client = make_client(lambda _: httpx.Response(500), retries=1)
    with pytest.raises(ProviderUnavailableError, match="500"):
        client.fetch_current(COORDS)


def test_falha_de_rede_e_repetida_e_depois_reportada() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("sem rota", request=request)

    with pytest.raises(ProviderUnavailableError, match="ConnectError"):
        make_client(handler, retries=2).fetch_current(COORDS)
    assert calls == 3


def test_401_nao_e_repetido() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"message": "Invalid API key"})

    with pytest.raises(AuthenticationError):
        make_client(handler).fetch_current(COORDS)
    assert calls == 1


def test_404_e_demais_4xx() -> None:
    with pytest.raises(ResourceNotFoundError):
        make_client(lambda _: httpx.Response(404)).fetch_current(COORDS)
    with pytest.raises(WeatherProviderError, match="400"):
        make_client(lambda _: httpx.Response(400)).fetch_current(COORDS)


def test_resposta_nao_json() -> None:
    client = make_client(lambda _: httpx.Response(200, content=b"<html>"))
    with pytest.raises(PayloadError, match="JSON"):
        client.fetch_current(COORDS)


def test_close_fecha_o_cliente_http(current_payload: dict[str, Any]) -> None:
    client = make_client(lambda _: httpx.Response(200, json=current_payload))
    client.close()
    with pytest.raises(RuntimeError):
        client.fetch_current(COORDS)
