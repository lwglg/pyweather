from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from pyweather_etl.application.use_cases import SyncOptions, SyncWeatherUseCase
from pyweather_etl.domain.entities import (
    CurrentSnapshot,
    CurrentWeather,
    DailyForecast,
    Forecast,
    HourlyForecast,
    Location,
    WeatherAlert,
)
from pyweather_etl.domain.errors import LocationNotFoundError, PyWeatherError
from pyweather_etl.domain.ports import GeocodingProvider, WeatherProvider, WeatherRepository
from pyweather_etl.domain.value_objects import (
    Coordinates,
    DailyTemperature,
    LocationSpec,
    TimezoneInfo,
)


NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
COORDS = Coordinates(-27.59, -48.54)
WEATHER = CurrentWeather(
    observed_at=NOW, temperature=24.0, feels_like=25.0, pressure=1015, humidity=60
)
TZ = TimezoneInfo("America/Sao_Paulo", -10800)
HOURLY = HourlyForecast(
    forecast_at=NOW, temperature=20.0, feels_like=20.0, pressure=1010, humidity=50
)
DAILY = DailyForecast(forecast_at=NOW, temperature=DailyTemperature(day=25.0))


class FakeGeocoder(GeocodingProvider):
    def __init__(self, location: Location | None = None) -> None:
        self.location = location
        self.calls = 0

    def locate(self, spec: LocationSpec) -> Location:
        self.calls += 1
        if self.location is None:
            raise LocationNotFoundError(spec.name)
        return self.location


class FakeProvider(WeatherProvider):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch_current(self, coordinates: Coordinates) -> CurrentSnapshot:
        self.calls.append("current")
        return CurrentSnapshot(WEATHER, TZ)

    def fetch_forecast(self, coordinates: Coordinates) -> Forecast:
        self.calls.append("forecast")
        return Forecast(steps=(HOURLY,), daily=(DAILY, DAILY))


class FakeRepository(WeatherRepository):
    def __init__(self, assign_id: int | None = 7) -> None:
        self.assign_id = assign_id
        self.upserts: list[Location] = []
        self.timezones: list[tuple[int, TimezoneInfo]] = []
        self.saved: dict[str, int] = {}

    def upsert_location(self, location: Location) -> Location:
        self.upserts.append(location)
        return replace(location, id=self.assign_id)

    def update_timezone(self, location_id: int, timezone: TimezoneInfo) -> None:
        self.timezones.append((location_id, timezone))

    def save_current(self, location_id: int, weather: CurrentWeather) -> int:
        self.saved["current"] = 1
        return 1

    def save_hourly(self, location_id: int, forecasts: Sequence[HourlyForecast]) -> int:
        self.saved["hourly"] = len(forecasts)
        return len(forecasts)

    def save_daily(self, location_id: int, forecasts: Sequence[DailyForecast]) -> int:
        self.saved["daily"] = len(forecasts)
        return len(forecasts)

    def save_alerts(self, location_id: int, alerts: Sequence[WeatherAlert]) -> int:
        self.saved["alerts"] = len(alerts)
        return len(alerts)


def build(
    *,
    spec: LocationSpec,
    geocoder: FakeGeocoder | None = None,
    provider: FakeProvider | None = None,
    repository: FakeRepository | None = None,
    options: SyncOptions | None = None,
) -> SyncWeatherUseCase:
    return SyncWeatherUseCase(
        geocoder=geocoder or FakeGeocoder(),
        provider=provider or FakeProvider(),
        repository=repository or FakeRepository(),
        spec=spec,
        options=options,
        clock=lambda: NOW,
    )


def test_fluxo_completo_com_geocodificacao() -> None:
    geocoder = FakeGeocoder(Location("Florianópolis", "BR", COORDS))
    provider = FakeProvider()
    repository = FakeRepository()
    use_case = build(
        spec=LocationSpec("Florianópolis", "BR"),
        geocoder=geocoder,
        provider=provider,
        repository=repository,
    )

    report = use_case.execute()

    assert geocoder.calls == 1
    assert provider.calls == ["current", "forecast"]
    assert repository.timezones == [(7, TZ)]
    assert (report.location_id, report.current, report.hourly, report.daily) == (7, 1, 1, 2)
    assert report.fetched_at == NOW


def test_coordenadas_informadas_dispensam_geocodificacao() -> None:
    geocoder = FakeGeocoder()
    repository = FakeRepository()
    use_case = build(
        spec=LocationSpec("Floripa", "BR", "SC", coordinates=COORDS),
        geocoder=geocoder,
        repository=repository,
    )

    use_case.execute()

    assert geocoder.calls == 0
    assert repository.upserts[0].coordinates == COORDS
    assert repository.upserts[0].state == "SC"


def test_local_e_resolvido_uma_unica_vez() -> None:
    geocoder = FakeGeocoder(Location("X", "BR", COORDS))
    repository = FakeRepository()
    use_case = build(spec=LocationSpec("X", "BR"), geocoder=geocoder, repository=repository)

    use_case.execute()
    use_case.execute()

    assert geocoder.calls == 1
    assert len(repository.upserts) == 1


def test_sem_previsao_consulta_apenas_condicoes_atuais() -> None:
    provider = FakeProvider()
    repository = FakeRepository()
    use_case = build(
        spec=LocationSpec("X", "BR", coordinates=COORDS),
        provider=provider,
        repository=repository,
        options=SyncOptions(include_forecast=False),
    )

    report = use_case.execute()

    assert provider.calls == ["current"]
    assert (report.hourly, report.daily) == (0, 0)
    assert "hourly" not in repository.saved


def test_cidade_nao_encontrada_propaga_erro() -> None:
    use_case = build(spec=LocationSpec("Nárnia", "BR"), geocoder=FakeGeocoder(None))
    with pytest.raises(LocationNotFoundError):
        use_case.execute()


def test_repositorio_sem_id_e_erro() -> None:
    use_case = build(
        spec=LocationSpec("X", "BR", coordinates=COORDS),
        repository=FakeRepository(assign_id=None),
    )
    with pytest.raises(PyWeatherError, match="identificador"):
        use_case.execute()
