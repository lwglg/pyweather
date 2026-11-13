"""Porta de leitura implementada pela infraestrutura."""

from abc import ABC, abstractmethod

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
    WeatherAlert,
)


class WeatherReadRepository(ABC):
    @abstractmethod
    def list_locations(self, flt: LocationFilter, page: Pagination) -> Page[Location]: ...

    @abstractmethod
    def get_location(self, location_id: int) -> Location | None: ...

    @abstractmethod
    def latest_current(self, location_id: int) -> CurrentWeather | None: ...

    @abstractmethod
    def list_current(
        self, location_id: int, flt: CurrentFilter, page: Pagination
    ) -> Page[CurrentWeather]: ...

    @abstractmethod
    def list_hourly(
        self, location_id: int, flt: HourlyFilter, page: Pagination
    ) -> Page[HourlyForecast]: ...

    @abstractmethod
    def list_daily(
        self, location_id: int, flt: DailyFilter, page: Pagination
    ) -> Page[DailyForecast]: ...

    @abstractmethod
    def list_alerts(
        self, location_id: int, flt: AlertFilter, page: Pagination
    ) -> Page[WeatherAlert]: ...

    @abstractmethod
    def ping(self) -> bool:
        """``True`` se o banco responde."""
