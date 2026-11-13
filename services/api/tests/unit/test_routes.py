from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pyweather_api.config import Settings, get_settings
from pyweather_api.infrastructure.persistence.repository import SqlModelWeatherReadRepository
from pyweather_api.main import create_app


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ok"}


def test_readiness_indisponivel() -> None:
    broken = SqlModelWeatherReadRepository(create_engine("postgresql+psycopg://u:p@127.0.0.1:1/db"))
    with TestClient(create_app(Settings(), repository=broken)) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["detail"] == "Banco de dados indisponível."


def test_list_locations(client: TestClient) -> None:
    body = client.get("/v1/locations", params={"country": "BR", "limit": 1}).json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert [item["name"] for item in body["items"]] == ["Curitiba"]


def test_get_location(client: TestClient) -> None:
    body = client.get("/v1/locations/1").json()
    assert body["name"] == "Florianópolis"
    assert body["timezone_offset"] == -10800


def test_local_inexistente_retorna_404_em_portugues(client: TestClient) -> None:
    response = client.get("/v1/locations/99")
    assert response.status_code == 404
    assert response.json() == {"detail": "Local 99 não encontrado."}


def test_id_invalido_retorna_422(client: TestClient) -> None:
    assert client.get("/v1/locations/0").status_code == 422
    assert client.get("/v1/locations/abc").status_code == 422


def test_current_mais_recente(client: TestClient) -> None:
    body = client.get("/v1/locations/1/current").json()
    assert body["temperature"] == 28.0
    assert body["condition"]["description"] == "chuva leve"
    assert body["observed_at"].endswith("Z") or body["observed_at"].endswith("+00:00")


def test_current_sem_dados_retorna_404(client: TestClient) -> None:
    response = client.get("/v1/locations/2/current")
    assert response.status_code == 404
    assert "Ainda não há condições atuais" in response.json()["detail"]


def test_current_history_com_filtros(client: TestClient) -> None:
    body = client.get(
        "/v1/locations/1/current/history",
        params={"min_temperature": 22, "max_temperature": 26, "order": "asc"},
    ).json()
    assert [item["temperature"] for item in body["items"]] == [22.0, 24.0, 26.0]
    assert body["total"] == 3


def test_periodo_sem_fuso_assume_utc(client: TestClient) -> None:
    response = client.get(
        "/v1/locations/1/current/history", params={"start": "2026-11-12T14:00:00"}
    )
    assert response.json()["total"] == 3  # 14h, 15h e 16h UTC


def test_periodo_invertido_retorna_422(client: TestClient) -> None:
    response = client.get(
        "/v1/locations/1/forecast/hourly",
        params={"start": "2026-11-13T00:00:00Z", "end": "2026-11-12T00:00:00Z"},
    )
    assert response.status_code == 422
    assert "início do período" in response.json()["detail"]


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 201},
        {"offset": -1},
        {"min_pop": 1.5},
        {"order": "sideways"},
        {"parametro_desconhecido": 1},
    ],
)
def test_parametros_invalidos_retornam_422(client: TestClient, params: dict[str, Any]) -> None:
    assert client.get("/v1/locations/1/forecast/hourly", params=params).status_code == 422


def test_hourly_e_daily(client: TestClient) -> None:
    hourly = client.get("/v1/locations/1/forecast/hourly", params={"min_pop": 0.75}).json()
    assert [item["pop"] for item in hourly["items"]] == [0.75, 1.0]

    daily = client.get("/v1/locations/1/forecast/daily", params={"max_temperature": 26}).json()
    assert daily["total"] == 2
    assert daily["items"][0]["moon_phase"] == 0.5


def test_alerts(client: TestClient) -> None:
    body = client.get("/v1/locations/1/alerts", params={"active_at": "2026-11-12T13:00:00Z"}).json()
    assert [item["alert_id"] for item in body["items"]] == ["A1"]
    assert body["items"][0]["descriptions"][0]["description"] == "Chuvas intensas."


def test_alerts_exige_fuso_em_active_at(client: TestClient) -> None:
    response = client.get("/v1/locations/1/alerts", params={"active_at": "2026-11-12T13:00:00"})
    assert response.status_code == 422


def test_openapi_documentado_em_portugues(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert "dados climáticos" in schema["info"]["description"]
    paths = schema["paths"]
    assert paths["/v1/locations"]["get"]["summary"] == "Lista os locais monitorados"
    assert paths["/health"]["get"]["tags"] == ["Saúde"]
    # parâmetros de consulta documentados em português
    params = {
        p["name"]: p
        for p in paths["/v1/locations/{location_id}/forecast/hourly"]["get"]["parameters"]
    }
    assert "Probabilidade mínima" in params["min_pop"]["description"]
    # campos continuam em inglês; descrições em português
    location = schema["components"]["schemas"]["LocationOut"]["properties"]
    assert "latitude" in location
    assert location["latitude"]["description"] == "Latitude em graus decimais."
    # respostas de erro documentadas
    assert "404" in paths["/v1/locations/{location_id}"]["get"]["responses"]


def test_cors_habilitado_somente_quando_configurado(
    repository: SqlModelWeatherReadRepository,
) -> None:
    settings = Settings(cors_origins="https://a.example, https://b.example")
    with TestClient(create_app(settings, repository=repository)) as client:
        response = client.get("/health", headers={"Origin": "https://a.example"})
    assert response.headers["access-control-allow-origin"] == "https://a.example"

    with TestClient(create_app(Settings(), repository=repository)) as client:
        response = client.get("/health", headers={"Origin": "https://a.example"})
    assert "access-control-allow-origin" not in response.headers


def test_lifespan_cria_engine_a_partir_da_configuracao(tmp_path: Any) -> None:
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'api.db'}")
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/ready").json() == {"status": "ok"}


def test_settings_url_postgres_e_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(postgres_user="u", postgres_password="s@nha", postgres_host="db")
    url = settings.sqlalchemy_url
    assert not isinstance(url, str)
    assert (url.drivername, url.host, url.password) == ("postgresql+psycopg", "db", "s@nha")
    assert Settings(database_url="sqlite://").sqlalchemy_url == "sqlite://"
    assert Settings(cors_origins=" , ").cors_origin_list == []

    get_settings.cache_clear()
    monkeypatch.setenv("API_TITLE", "Teste")
    assert get_settings() is get_settings()
    assert get_settings().api_title == "Teste"
    get_settings.cache_clear()
