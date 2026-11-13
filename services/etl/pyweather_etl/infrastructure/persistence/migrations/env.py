"""Ambiente Alembic: usa a ``Engine`` injetada em ``config.attributes['engine']``."""

from alembic import context

from pyweather_etl.infrastructure.persistence.models import Base


config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = config.attributes.get("engine")
    if engine is None:
        raise RuntimeError("Nenhuma Engine foi informada ao ambiente de migração.")

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("O modo offline não é suportado; use upgrade_to_head(engine).")

run_migrations_online()
