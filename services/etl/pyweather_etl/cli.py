"""Interface de linha de comando do ETL.

Comandos:
  migrate      aplica as migrações do banco
  run          migra e executa uma extração única
  serve        migra e executa extrações periódicas (modo contêiner)
  healthcheck  retorna 0 se o banco está acessível e migrado
"""

import argparse
import logging
import signal
from collections.abc import Callable, Sequence

from sqlalchemy.exc import SQLAlchemyError

from pyweather_etl import composition
from pyweather_etl.application.scheduler import PeriodicRunner
from pyweather_etl.config import Settings, get_settings
from pyweather_etl.domain.errors import PyWeatherError
from pyweather_etl.infrastructure.persistence.schema import is_up_to_date, upgrade_to_head


logger = logging.getLogger(__name__)


def migrate(settings: Settings) -> int:
    engine = composition.build_engine(settings)
    try:
        upgrade_to_head(engine)
    finally:
        engine.dispose()
    logger.info("Banco de dados migrado para a revisão mais recente.")
    return 0


def run_once(settings: Settings) -> int:
    engine = composition.build_engine(settings)
    try:
        upgrade_to_head(engine)
        use_case, client = composition.build_use_case(settings, engine)
        try:
            use_case.execute()
        finally:
            client.close()
    finally:
        engine.dispose()
    return 0


def serve(settings: Settings, max_runs: int | None = None) -> int:
    engine = composition.build_engine(settings)
    try:
        upgrade_to_head(engine)
        use_case, client = composition.build_use_case(settings, engine)
        runner = PeriodicRunner(use_case.execute, settings.etl_interval_seconds)
        _stop_on_signals(runner)
        logger.info("ETL iniciado; intervalo de %ds.", settings.etl_interval_seconds)
        try:
            runner.run(max_runs=max_runs)
        finally:
            client.close()
    finally:
        engine.dispose()
    return 0


def healthcheck(settings: Settings) -> int:
    engine = composition.build_engine(settings)
    try:
        return 0 if is_up_to_date(engine) else 1
    except SQLAlchemyError:
        return 1
    finally:
        engine.dispose()


def _stop_on_signals(runner: PeriodicRunner) -> None:
    def handler(signum: int, _frame: object) -> None:
        logger.info("Sinal %d recebido; encerrando após a execução atual.", signum)
        runner.stop()

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


COMMANDS: dict[str, Callable[[Settings], int]] = {
    "migrate": migrate,
    "run": run_once,
    "serve": serve,
    "healthcheck": healthcheck,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyweather-etl",
        description="ETL de dados climáticos: OpenWeather One Call 4.0 → PostgreSQL.",
    )
    parser.add_argument("command", choices=sorted(COMMANDS), help="comando a executar")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    composition.configure_logging(settings.log_level)
    try:
        return COMMANDS[args.command](settings)
    except PyWeatherError as exc:
        logger.error("%s", exc)
        return 1
