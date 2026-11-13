from threading import Event

import pytest

from pyweather_etl.application.scheduler import PeriodicRunner


def test_intervalo_deve_ser_positivo() -> None:
    with pytest.raises(ValueError, match="positivo"):
        PeriodicRunner(lambda: None, 0)


def test_executa_ate_max_runs() -> None:
    calls: list[int] = []
    runner = PeriodicRunner(lambda: calls.append(1), interval_seconds=0.001)

    assert runner.run(max_runs=3) == 3
    assert len(calls) == 3


def test_falha_no_job_nao_encerra_o_laco(caplog: pytest.LogCaptureFixture) -> None:
    calls = 0

    def job() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")

    runner = PeriodicRunner(job, interval_seconds=0.001)

    assert runner.run(max_runs=2) == 2
    assert "Falha na execução do ETL" in caplog.text


def test_stop_interrompe_a_espera() -> None:
    stop = Event()
    runner = PeriodicRunner(lambda: None, interval_seconds=3600, stop_event=stop)

    def job() -> None:
        runner.stop()

    runner = PeriodicRunner(job, interval_seconds=3600, stop_event=stop)

    assert runner.run() == 1  # não espera 1h: o stop encerra a espera imediatamente
    assert runner.stopped


def test_nao_executa_se_ja_parado() -> None:
    stop = Event()
    stop.set()
    runner = PeriodicRunner(lambda: pytest.fail("não deve executar"), 1, stop_event=stop)
    assert runner.run() == 0
