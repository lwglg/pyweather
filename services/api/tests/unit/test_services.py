from datetime import UTC, datetime, timedelta

import pytest

from pyweather_api.application.services import WeatherQueryService
from pyweather_api.domain.errors import InvalidFilterError, LocationNotFoundError, NoDataError
from pyweather_api.domain.models import (
    AlertFilter,
    CurrentFilter,
    DailyFilter,
    HourlyFilter,
    LocationFilter,
    Pagination,
    TimeRange,
)
from pyweather_api.infrastructure.persistence.repository import SqlModelWeatherReadRepository


T0 = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
PAGE = Pagination()


@pytest.fixture
def service(repository: SqlModelWeatherReadRepository) -> WeatherQueryService:
    return WeatherQueryService(repository)


def test_list_e_get_location(service: WeatherQueryService) -> None:
    assert service.list_locations(LocationFilter(), PAGE).total == 3
    assert service.get_location(1).name == "Florianópolis"


def test_local_inexistente(service: WeatherQueryService) -> None:
    with pytest.raises(LocationNotFoundError, match="99"):
        service.get_location(99)
    with pytest.raises(LocationNotFoundError):
        service.list_hourly(99, HourlyFilter(), PAGE)
    with pytest.raises(LocationNotFoundError):
        service.list_alerts(99, AlertFilter(), PAGE)


def test_local_sem_dados(service: WeatherQueryService) -> None:
    with pytest.raises(NoDataError, match="condições atuais"):
        service.latest_current(2)


def test_latest_current(service: WeatherQueryService) -> None:
    assert service.latest_current(1).temperature == 28.0


def test_periodo_invertido_e_rejeitado(service: WeatherQueryService) -> None:
    inverted = TimeRange(start=T0 + timedelta(days=1), end=T0)
    with pytest.raises(InvalidFilterError, match="período"):
        service.list_current(1, CurrentFilter(period=inverted), PAGE)
    with pytest.raises(InvalidFilterError):
        service.list_hourly(1, HourlyFilter(period=inverted), PAGE)
    with pytest.raises(InvalidFilterError):
        service.list_daily(1, DailyFilter(period=inverted), PAGE)


def test_limites_invertidos_sao_rejeitados(service: WeatherQueryService) -> None:
    with pytest.raises(InvalidFilterError, match="temperatura"):
        service.list_current(1, CurrentFilter(min_temperature=30, max_temperature=10), PAGE)
    with pytest.raises(InvalidFilterError, match="umidade"):
        service.list_current(1, CurrentFilter(min_humidity=90, max_humidity=10), PAGE)
    with pytest.raises(InvalidFilterError, match="temperatura"):
        service.list_hourly(1, HourlyFilter(min_temperature=30, max_temperature=10), PAGE)
    with pytest.raises(InvalidFilterError, match="temperatura"):
        service.list_daily(1, DailyFilter(min_temperature=30, max_temperature=10), PAGE)


def test_listagens_validas(service: WeatherQueryService) -> None:
    assert service.list_current(1, CurrentFilter(), PAGE).total == 5
    assert service.list_hourly(1, HourlyFilter(), PAGE).total == 5
    assert service.list_daily(1, DailyFilter(), PAGE).total == 5
    assert service.list_alerts(1, AlertFilter(), PAGE).total == 2


def test_saude(service: WeatherQueryService) -> None:
    assert service.is_healthy() is True
