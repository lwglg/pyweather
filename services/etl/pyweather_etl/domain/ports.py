"""Portas (interfaces) exigidas pelo domínio; implementadas na camada de infraestrutura."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from pyweather_etl.domain.entities import (
    CurrentSnapshot,
    CurrentWeather,
    DailyForecast,
    Forecast,
    HourlyForecast,
    Location,
    WeatherAlert,
)
from pyweather_etl.domain.value_objects import Coordinates, LocationSpec, TimezoneInfo


class GeocodingProvider(ABC):
    """Resolve o nome de uma cidade em coordenadas geográficas."""

    @abstractmethod
    def locate(self, spec: LocationSpec) -> Location:
        """Retorna o local correspondente ou levanta ``LocationNotFoundError``."""


class WeatherProvider(ABC):
    """Fonte de dados climáticos (OpenWeather, plano gratuito)."""

    @abstractmethod
    def fetch_current(self, coordinates: Coordinates) -> CurrentSnapshot:
        """Condições atuais e fuso horário do local."""

    @abstractmethod
    def fetch_forecast(self, coordinates: Coordinates) -> Forecast:
        """Previsão de 5 dias: passos de 3 h e resumo diário."""


class WeatherRepository(ABC):
    """Persistência dos dados climáticos. Todas as gravações são idempotentes (upsert)."""

    @abstractmethod
    def upsert_location(self, location: Location) -> Location:
        """Cria/atualiza o local e o retorna com ``id`` preenchido."""

    @abstractmethod
    def update_timezone(self, location_id: int, timezone: TimezoneInfo) -> None:
        """Atualiza o fuso horário do local."""

    @abstractmethod
    def save_current(self, location_id: int, weather: CurrentWeather) -> int:
        """Grava a observação atual; retorna o número de registros gravados."""

    @abstractmethod
    def save_hourly(self, location_id: int, forecasts: Sequence[HourlyForecast]) -> int:
        """Grava previsões horárias; retorna o número de registros gravados."""

    @abstractmethod
    def save_daily(self, location_id: int, forecasts: Sequence[DailyForecast]) -> int:
        """Grava previsões diárias; retorna o número de registros gravados."""

    @abstractmethod
    def save_alerts(self, location_id: int, alerts: Sequence[WeatherAlert]) -> int:
        """Grava alertas; retorna o número de registros gravados."""
