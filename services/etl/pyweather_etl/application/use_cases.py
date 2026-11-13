"""Caso de uso principal: sincronizar os dados climáticos de uma cidade."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from pyweather_etl.domain.entities import Location
from pyweather_etl.domain.errors import PyWeatherError
from pyweather_etl.domain.ports import GeocodingProvider, WeatherProvider, WeatherRepository
from pyweather_etl.domain.value_objects import LocationSpec


logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class SyncOptions:
    """Parâmetros da extração. A previsão custa 1 chamada da API; as condições atuais, outra."""

    include_forecast: bool = True


@dataclass(frozen=True, slots=True)
class SyncReport:
    """Resumo de uma execução do ETL."""

    location_id: int
    fetched_at: datetime
    current: int
    hourly: int
    daily: int


class SyncWeatherUseCase:
    """Extrai (E) da OpenWeather, transforma (T) em entidades de domínio e carrega (L) no banco."""

    def __init__(
        self,
        *,
        geocoder: GeocodingProvider,
        provider: WeatherProvider,
        repository: WeatherRepository,
        spec: LocationSpec,
        options: SyncOptions | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._geocoder = geocoder
        self._provider = provider
        self._repository = repository
        self._spec = spec
        self._options = options or SyncOptions()
        self._clock = clock
        self._location: Location | None = None

    def execute(self) -> SyncReport:
        """Executa uma sincronização completa. Idempotente: reexecutar não duplica registros."""
        location = self._resolve_location()
        location_id = self._require_id(location)
        coordinates = location.coordinates

        snapshot = self._provider.fetch_current(coordinates)
        self._repository.update_timezone(location_id, snapshot.timezone)
        current = self._repository.save_current(location_id, snapshot.weather)

        hourly = daily = 0
        if self._options.include_forecast:
            forecast = self._provider.fetch_forecast(coordinates)
            hourly = self._repository.save_hourly(location_id, forecast.steps)
            daily = self._repository.save_daily(location_id, forecast.daily)

        report = SyncReport(
            location_id=location_id,
            fetched_at=self._clock(),
            current=current,
            hourly=hourly,
            daily=daily,
        )
        logger.info(
            "Sincronização concluída: local=%s atual=%d previsão-passos=%d previsão-diária=%d",
            location_id,
            report.current,
            report.hourly,
            report.daily,
        )
        return report

    def _resolve_location(self) -> Location:
        """Resolve (uma única vez) e persiste o local-alvo."""
        if self._location is None:
            if self._spec.coordinates is not None:
                location = Location(
                    name=self._spec.name,
                    country=self._spec.country,
                    state=self._spec.state,
                    coordinates=self._spec.coordinates,
                )
            else:
                location = self._geocoder.locate(self._spec)
            self._location = self._repository.upsert_location(location)
        return self._location

    @staticmethod
    def _require_id(location: Location) -> int:
        if location.id is None:
            raise PyWeatherError("O repositório devolveu um local sem identificador.")
        return location.id
