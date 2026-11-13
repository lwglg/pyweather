"""Agendador periódico simples e interrompível (adequado a um contêiner de longa duração)."""

import logging
from collections.abc import Callable
from threading import Event


logger = logging.getLogger(__name__)


class PeriodicRunner:
    """Executa ``job`` a cada ``interval_seconds``; falhas são registradas e não encerram o laço."""

    def __init__(
        self,
        job: Callable[[], object],
        interval_seconds: float,
        stop_event: Event | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("O intervalo deve ser positivo.")
        self._job = job
        self._interval = interval_seconds
        self._stop = stop_event or Event()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def stop(self) -> None:
        """Solicita o encerramento; a espera entre execuções é interrompida imediatamente."""
        self._stop.set()

    def run(self, max_runs: int | None = None) -> int:
        """Executa o laço e retorna o número de execuções realizadas."""
        runs = 0
        while not self._stop.is_set():
            self._run_once()
            runs += 1
            if max_runs is not None and runs >= max_runs:
                break
            self._stop.wait(self._interval)
        return runs

    def _run_once(self) -> None:
        try:
            self._job()
        except Exception:
            logger.exception("Falha na execução do ETL; nova tentativa no próximo ciclo.")
