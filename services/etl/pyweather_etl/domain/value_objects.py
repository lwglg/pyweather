"""Objetos de valor: imutáveis, sem identidade, comparados por valor."""

from dataclasses import dataclass

from pyweather_etl.domain.errors import InvalidCoordinatesError


@dataclass(frozen=True, slots=True)
class Coordinates:
    """Par latitude/longitude em graus decimais."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise InvalidCoordinatesError(f"Latitude fora do intervalo [-90, 90]: {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise InvalidCoordinatesError(
                f"Longitude fora do intervalo [-180, 180]: {self.longitude}"
            )


@dataclass(frozen=True, slots=True)
class LocationSpec:
    """Descrição da cidade-alvo da extração.

    Se ``coordinates`` estiver presente, a geocodificação é dispensada.
    """

    name: str
    country: str
    state: str | None = None
    coordinates: Coordinates | None = None


@dataclass(frozen=True, slots=True)
class TimezoneInfo:
    """Fuso horário do local (nome IANA e deslocamento em segundos em relação a UTC)."""

    name: str
    offset_seconds: int


@dataclass(frozen=True, slots=True)
class WeatherCondition:
    """Condição meteorológica (código, grupo, descrição localizada e ícone)."""

    code: int
    main: str
    description: str
    icon: str


@dataclass(frozen=True, slots=True)
class Wind:
    """Vento: velocidade e rajada (m/s no sistema métrico) e direção em graus."""

    speed: float | None = None
    direction: int | None = None
    gust: float | None = None


@dataclass(frozen=True, slots=True)
class Precipitation:
    """Precipitação (mm/h) e probabilidade de ocorrência (0–1)."""

    rain: float | None = None
    snow: float | None = None
    probability: float | None = None


@dataclass(frozen=True, slots=True)
class DailyTemperature:
    """Temperaturas ao longo do dia (manhã, dia, tarde/noite, noite) com mínima e máxima."""

    day: float | None = None
    min: float | None = None
    max: float | None = None
    night: float | None = None
    evening: float | None = None
    morning: float | None = None


@dataclass(frozen=True, slots=True)
class DailyFeelsLike:
    """Sensação térmica por período do dia."""

    day: float | None = None
    night: float | None = None
    evening: float | None = None
    morning: float | None = None


@dataclass(frozen=True, slots=True)
class AlertDescription:
    """Texto de um alerta em um idioma específico."""

    language: str
    text: str
