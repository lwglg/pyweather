from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine

from pyweather_api.domain.models import (
    AlertFilter,
    CurrentFilter,
    DailyFilter,
    HourlyFilter,
    LocationFilter,
    Pagination,
    SortOrder,
    TimeRange,
)
from pyweather_api.infrastructure.persistence.repository import (
    SqlModelWeatherReadRepository,
    _like,
)


T0 = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
ALL = Pagination(limit=50, offset=0)


def test_locations_ordenadas_por_nome(repository: SqlModelWeatherReadRepository) -> None:
    page = repository.list_locations(LocationFilter(), ALL)
    assert [loc.name for loc in page.items] == ["Austin", "Curitiba", "Florianópolis"]
    assert page.total == 3


def test_locations_filtros(repository: SqlModelWeatherReadRepository) -> None:
    by_name = repository.list_locations(LocationFilter(name="florian"), ALL)
    by_state = repository.list_locations(LocationFilter(state="para"), ALL)
    by_country = repository.list_locations(LocationFilter(country="us"), ALL)

    assert [loc.id for loc in by_name.items] == [1]
    assert [loc.id for loc in by_state.items] == [2]
    assert [loc.id for loc in by_country.items] == [3]


def test_locations_paginacao(repository: SqlModelWeatherReadRepository) -> None:
    page = repository.list_locations(LocationFilter(), Pagination(limit=1, offset=1))
    assert [loc.name for loc in page.items] == ["Curitiba"]
    assert (page.total, page.limit, page.offset) == (3, 1, 1)


def test_curinga_like_e_escapado(repository: SqlModelWeatherReadRepository) -> None:
    assert _like("50%_") == "%50\\%\\_%"
    assert repository.list_locations(LocationFilter(name="%"), ALL).total == 0


def test_get_location(repository: SqlModelWeatherReadRepository) -> None:
    location = repository.get_location(1)
    assert location is not None
    assert location.timezone == "America/Sao_Paulo"
    assert repository.get_location(99) is None


def test_latest_current(repository: SqlModelWeatherReadRepository) -> None:
    latest = repository.latest_current(1)
    assert latest is not None
    assert latest.temperature == 28.0
    assert latest.observed_at == T0 + timedelta(hours=4)
    assert latest.observed_at.tzinfo is UTC  # SQLite devolve datas ingênuas; o mapper normaliza
    assert latest.condition.main == "Rain"
    assert repository.latest_current(2) is None


def test_current_filtros_combinados(repository: SqlModelWeatherReadRepository) -> None:
    flt = CurrentFilter(min_temperature=22, max_temperature=26, order=SortOrder.ASC)
    page = repository.list_current(1, flt, ALL)
    assert [item.temperature for item in page.items] == [22.0, 24.0, 26.0]

    humidity = repository.list_current(1, CurrentFilter(min_humidity=70, max_humidity=80), ALL)
    assert humidity.total == 2

    period = CurrentFilter(period=TimeRange(start=T0 + timedelta(hours=3)))
    assert repository.list_current(1, period, ALL).total == 2

    ended = CurrentFilter(period=TimeRange(end=T0 + timedelta(hours=1)))
    assert repository.list_current(1, ended, ALL).total == 2


def test_current_condicao_busca_grupo_e_descricao(
    repository: SqlModelWeatherReadRepository,
) -> None:
    assert repository.list_current(1, CurrentFilter(condition="rain"), ALL).total == 3
    assert repository.list_current(1, CurrentFilter(condition="céu"), ALL).total == 2


def test_current_ordem_padrao_descendente(repository: SqlModelWeatherReadRepository) -> None:
    page = repository.list_current(1, CurrentFilter(), ALL)
    assert page.items[0].temperature == 28.0


def test_hourly_filtros(repository: SqlModelWeatherReadRepository) -> None:
    page = repository.list_hourly(1, HourlyFilter(min_pop=0.5), ALL)
    assert [item.pop for item in page.items] == [0.5, 0.75, 1.0]

    temps = repository.list_hourly(
        1, HourlyFilter(min_temperature=19, max_temperature=20, order=SortOrder.DESC), ALL
    )
    assert [item.temperature for item in temps.items] == [20.0, 19.0]

    assert repository.list_hourly(1, HourlyFilter(condition="nublado"), ALL).total == 5


def test_daily_filtros(repository: SqlModelWeatherReadRepository) -> None:
    page = repository.list_daily(1, DailyFilter(min_temperature=17, max_temperature=28), ALL)
    assert [item.temp_min for item in page.items] == [17.0, 18.0]  # máx ≤ 28 → dias 2 e 3

    rainy = repository.list_daily(1, DailyFilter(min_pop=0.75), ALL)
    assert rainy.total == 2
    assert rainy.items[0].moon_phase == 0.5


def test_alerts_filtros(repository: SqlModelWeatherReadRepository) -> None:
    everything = repository.list_alerts(1, AlertFilter(), ALL)
    assert [a.alert_id for a in everything.items] == ["A2", "A1"]  # mais recente primeiro

    active = repository.list_alerts(1, AlertFilter(active_at=T0 + timedelta(hours=1)), ALL)
    assert [a.alert_id for a in active.items] == ["A1"]
    assert active.items[0].descriptions[0].language == "pt-BR"
    assert active.items[0].tags == ("Rain",)

    assert repository.list_alerts(1, AlertFilter(event="vendaval"), ALL).total == 1
    assert repository.list_alerts(1, AlertFilter(sender="inmet"), ALL).total == 1


def test_ping(repository: SqlModelWeatherReadRepository) -> None:
    assert repository.ping() is True


def test_ping_falha_sem_banco() -> None:
    broken = SqlModelWeatherReadRepository(create_engine("postgresql+psycopg://u:p@127.0.0.1:1/db"))
    assert broken.ping() is False
