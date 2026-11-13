"""Gestão do esquema via Alembic (executada programaticamente, sem ``alembic.ini``)."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine


MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _config(engine: Engine | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    if engine is not None:
        config.attributes["engine"] = engine
    return config


def head_revision() -> str | None:
    """Revisão mais recente conhecida pelo código."""
    return ScriptDirectory.from_config(_config()).get_current_head()


def upgrade_to_head(engine: Engine) -> None:
    """Aplica todas as migrações pendentes (idempotente)."""
    command.upgrade(_config(engine), "head")


def is_up_to_date(engine: Engine) -> bool:
    """``True`` se o banco está na revisão mais recente."""
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    return current == head_revision()
