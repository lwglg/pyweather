import signal
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from pyweather_etl import cli, composition
from pyweather_etl.config import Settings, get_settings
from pyweather_etl.infrastructure.openweather.client import OpenWeatherClient
from pyweather_etl.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
)
from pyweather_etl.infrastructure.persistence.models import CurrentWeatherModel, LocationModel


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'etl.db'}",
        openweather_api_key="k",
        city_latitude=-27.59,
        city_longitude=-48.54,
        etl_interval_seconds=60,
    )


def count(settings: Settings, model: type) -> int:
    engine = create_db_engine(settings.sqlalchemy_url)
    try:
        with create_session_factory(engine)() as session:
            return session.scalar(select(func.count()).select_from(model)) or 0
    finally:
        engine.dispose()


def patch_http(monkeypatch: pytest.MonkeyPatch, payloads: dict[str, object]) -> None:
    """Substitui o transporte HTTP do cliente por respostas fixas, por sufixo de caminho."""

    def handler(request: httpx.Request) -> httpx.Response:
        for suffix, body in payloads.items():
            if request.url.path.endswith(suffix):
                return httpx.Response(200, json=body)
        return httpx.Response(404)

    original = OpenWeatherClient.__init__

    def init(self: OpenWeatherClient, api_key: str, **kwargs: object) -> None:
        kwargs["client"] = httpx.Client(
            base_url="https://api.test", transport=httpx.MockTransport(handler)
        )
        original(self, api_key, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(OpenWeatherClient, "__init__", init)


@pytest.fixture
def http_payloads(
    current_payload: dict[str, object], hourly_record: dict[str, object]
) -> dict[str, object]:
    return {
        "/current": current_payload,
        "/1h": {"data": [hourly_record]},
        "/1day": {"data": []},
        "/ALERT-1": {"id": "ALERT-1", "start": 1, "end": 2},
        "/ALERT-2": {"id": "ALERT-2", "start": 1, "end": 2},
    }


def test_migrate(settings: Settings) -> None:
    assert cli.migrate(settings) == 0
    assert count(settings, LocationModel) == 0


def test_run_once_extrai_e_persiste(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, http_payloads: dict[str, object]
) -> None:
    patch_http(monkeypatch, http_payloads)

    assert cli.run_once(settings) == 0
    assert cli.run_once(settings) == 0  # idempotente

    assert count(settings, LocationModel) == 1
    assert count(settings, CurrentWeatherModel) == 1


def test_serve_executa_e_encerra(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, http_payloads: dict[str, object]
) -> None:
    patch_http(monkeypatch, http_payloads)
    monkeypatch.setattr(cli, "_stop_on_signals", lambda runner: None)

    assert cli.serve(settings, max_runs=1) == 0
    assert count(settings, CurrentWeatherModel) == 1


def test_stop_on_signals_registra_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    from pyweather_etl.application.scheduler import PeriodicRunner

    registered: dict[int, object] = {}
    monkeypatch.setattr(signal, "signal", lambda sig, handler: registered.setdefault(sig, handler))
    runner = PeriodicRunner(lambda: None, 1)

    cli._stop_on_signals(runner)
    handler = registered[signal.SIGTERM]
    handler(15, None)  # type: ignore[operator]

    assert runner.stopped


def test_healthcheck(settings: Settings) -> None:
    assert cli.healthcheck(settings) == 1  # banco sem migrações
    cli.migrate(settings)
    assert cli.healthcheck(settings) == 0


def test_healthcheck_banco_inacessivel() -> None:
    broken = Settings(database_url="postgresql+psycopg://u:p@127.0.0.1:1/db")
    assert cli.healthcheck(broken) == 1


def test_main_converte_erro_de_dominio_em_codigo_de_saida(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'x.db'}")
    monkeypatch.setenv("OPENWEATHER_API_KEY", "")
    get_settings.cache_clear()

    assert cli.main(["run"]) == 1  # ConfigurationError: sem chave

    get_settings.cache_clear()


def test_main_executa_comando(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'y.db'}")
    get_settings.cache_clear()

    assert cli.main(["migrate"]) == 0

    get_settings.cache_clear()


def test_parser_rejeita_comando_desconhecido() -> None:
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["inexistente"])


def test_configure_logging_silencia_httpx() -> None:
    import logging

    composition.configure_logging("DEBUG")
    assert logging.getLogger("httpx").level == logging.WARNING
