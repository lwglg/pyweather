"""Criação de engine e fábrica de sessões."""

from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(url: str | URL) -> Engine:
    """Engine com ``pool_pre_ping`` para tolerar reinícios do banco em contêineres."""
    return create_engine(url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
