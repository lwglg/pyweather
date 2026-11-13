"""Casos de uso de consulta. Validam regras de negócio e delegam ao repositório."""

from pyweather_api.domain.errors import InvalidFilterError, LocationNotFoundError, NoDataError
from pyweather_api.domain.models import (
    AlertFilter,
    CurrentFilter,
    CurrentWeather,
    DailyFilter,
    DailyForecast,
    HourlyFilter,
    HourlyForecast,
    Location,
    LocationFilter,
    Page,
    Pagination,
    TimeRange,
    WeatherAlert,
)
from pyweather_api.domain.ports import WeatherReadRepository


def _check_range(period: TimeRange) -> None:
    if period.start and period.end and period.start > period.end:
        raise InvalidFilterError("O início do período não pode ser posterior ao fim.")


def _check_bounds(low: float | None, high: float | None, name: str) -> None:
    if low is not None and high is not None and low > high:
        raise InvalidFilterError(f"O valor mínimo de {name} não pode exceder o máximo.")


class WeatherQueryService:
    def __init__(self, repository: WeatherReadRepository) -> None:
        self._repo = repository

    # --- Locais --------------------------------------------------------------------------------
    def list_locations(self, flt: LocationFilter, page: Pagination) -> Page[Location]:
        return self._repo.list_locations(flt, page)

    def get_location(self, location_id: int) -> Location:
        return self._require_location(location_id)

    # --- Séries --------------------------------------------------------------------------------
    def latest_current(self, location_id: int) -> CurrentWeather:
        self._require_location(location_id)
        latest = self._repo.latest_current(location_id)
        if latest is None:
            raise NoDataError(location_id, "condições atuais")
        return latest

    def list_current(
        self, location_id: int, flt: CurrentFilter, page: Pagination
    ) -> Page[CurrentWeather]:
        self._require_location(location_id)
        _check_range(flt.period)
        _check_bounds(flt.min_temperature, flt.max_temperature, "temperatura")
        _check_bounds(flt.min_humidity, flt.max_humidity, "umidade")
        return self._repo.list_current(location_id, flt, page)

    def list_hourly(
        self, location_id: int, flt: HourlyFilter, page: Pagination
    ) -> Page[HourlyForecast]:
        self._require_location(location_id)
        _check_range(flt.period)
        _check_bounds(flt.min_temperature, flt.max_temperature, "temperatura")
        return self._repo.list_hourly(location_id, flt, page)

    def list_daily(
        self, location_id: int, flt: DailyFilter, page: Pagination
    ) -> Page[DailyForecast]:
        self._require_location(location_id)
        _check_range(flt.period)
        _check_bounds(flt.min_temperature, flt.max_temperature, "temperatura")
        return self._repo.list_daily(location_id, flt, page)

    def list_alerts(
        self, location_id: int, flt: AlertFilter, page: Pagination
    ) -> Page[WeatherAlert]:
        self._require_location(location_id)
        return self._repo.list_alerts(location_id, flt, page)

    # --- Saúde ---------------------------------------------------------------------------------
    def is_healthy(self) -> bool:
        return self._repo.ping()

    def _require_location(self, location_id: int) -> Location:
        location = self._repo.get_location(location_id)
        if location is None:
            raise LocationNotFoundError(location_id)
        return location
