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
    """Parâmetros de volume da extração (cada página consome uma chamada da API)."""

    hourly_pages: int = 3
    daily_pages: int = 1
    include_alerts: bool = True


@dataclass(frozen=True, slots=True)
class SyncReport:
    """Resumo de uma execução do ETL."""

    location_id: int
    fetched_at: datetime
    current: int
    hourly: int
    daily: int
    alerts: int


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

        hourly = 0
        if self._options.hourly_pages > 0:
            forecasts = self._provider.fetch_hourly(coordinates, self._options.hourly_pages)
            hourly = self._repository.save_hourly(location_id, forecasts)

        daily = 0
        if self._options.daily_pages > 0:
            daily_forecasts = self._provider.fetch_daily(coordinates, self._options.daily_pages)
            daily = self._repository.save_daily(location_id, daily_forecasts)

        alerts = 0
        if self._options.include_alerts and snapshot.alert_ids:
            found = self._provider.fetch_alerts(snapshot.alert_ids)
            alerts = self._repository.save_alerts(location_id, found)

        report = SyncReport(
            location_id=location_id,
            fetched_at=self._clock(),
            current=current,
            hourly=hourly,
            daily=daily,
            alerts=alerts,
        )
        logger.info(
            "Sincronização concluída: local=%s atual=%d horária=%d diária=%d alertas=%d",
            location_id,
            report.current,
            report.hourly,
            report.daily,
            report.alerts,
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
