"""Cliente HTTP da OpenWeather, plano gratuito (extração — E do ETL).

APIs usadas (todas disponíveis na chave gratuita): Geocoding, Current Weather Data 2.5 e
5 Day / 3 Hour Forecast 2.5.
"""

import logging
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from pyweather_etl.domain.entities import (
    CurrentSnapshot,
    Forecast,
    Location,
)
from pyweather_etl.domain.errors import (
    AuthenticationError,
    ConfigurationError,
    LocationNotFoundError,
    PayloadError,
    ProviderUnavailableError,
    RateLimitError,
    ResourceNotFoundError,
    WeatherProviderError,
)
from pyweather_etl.domain.ports import GeocodingProvider, WeatherProvider
from pyweather_etl.domain.value_objects import Coordinates, LocationSpec
from pyweather_etl.infrastructure.openweather import mappers


logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.openweathermap.org"
CURRENT_WEATHER = "/data/2.5/weather"
FORECAST = "/data/2.5/forecast"
GEOCODING = "/geo/1.0/direct"

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_RETRY_AFTER_SECONDS = 60.0


class OpenWeatherClient(GeocodingProvider, WeatherProvider):
    """Implementa as portas ``GeocodingProvider`` e ``WeatherProvider``.

    Boas práticas aplicadas:
      * a chave (``appid``) é enviada apenas como parâmetro de consulta e nunca é logada;
      * tentativas com recuo exponencial para HTTP 429/5xx e falhas de rede.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        units: str = "metric",
        lang: str = "pt_br",
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ConfigurationError(
                "A chave da OpenWeather não foi informada (variável OPENWEATHER_API_KEY)."
            )
        self._api_key = api_key
        self._base_url = base_url
        self._units = units
        self._lang = lang
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self._sleep = sleep
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    # --- GeocodingProvider ---------------------------------------------------------------------
    def locate(self, spec: LocationSpec) -> Location:
        # A API só aceita o estado como parte da consulta para os EUA.
        parts = [spec.name]
        if spec.state and spec.country.upper() == "US":
            parts.append(spec.state)
        parts.append(spec.country)
        query = ",".join(parts)

        payload = self._request(GEOCODING, {"q": query, "limit": 1})
        if not isinstance(payload, list) or not payload:
            raise LocationNotFoundError(f"Cidade não encontrada pelo geocodificador: {query!r}.")
        return mappers.map_geocoding_item(payload[0], spec)

    # --- WeatherProvider -----------------------------------------------------------------------
    def fetch_current(self, coordinates: Coordinates) -> CurrentSnapshot:
        payload = self._request(CURRENT_WEATHER, self._weather_params(coordinates))
        return mappers.map_current_snapshot(payload)

    def fetch_forecast(self, coordinates: Coordinates) -> Forecast:
        payload = self._request(FORECAST, self._weather_params(coordinates))
        return mappers.map_forecast(payload)

    # --- Internos ------------------------------------------------------------------------------
    def _weather_params(self, coordinates: Coordinates) -> dict[str, Any]:
        return {
            "lat": coordinates.latitude,
            "lon": coordinates.longitude,
            "units": self._units,
            "lang": self._lang,
        }

    def _request(self, path: str, params: Mapping[str, Any]) -> Any:
        query = {**params, "appid": self._api_key}
        last_error: WeatherProviderError | None = None

        for attempt in range(self._max_retries + 1):
            delay: float | None = None
            try:
                response = self._client.get(path, params=query)
            except httpx.TransportError as exc:
                last_error = ProviderUnavailableError(
                    f"Falha de rede ao consultar {path}: {type(exc).__name__}."
                )
            else:
                if response.status_code not in _RETRYABLE_STATUS:
                    return self._parse(response, path)
                last_error = self._retryable_error(response, path)
                delay = self._retry_after(response)

            if attempt < self._max_retries:
                wait = delay if delay is not None else self._backoff * (2**attempt)
                logger.warning(
                    "Tentativa %d/%d falhou em %s; nova tentativa em %.1fs.",
                    attempt + 1,
                    self._max_retries + 1,
                    path,
                    wait,
                )
                self._sleep(wait)

        assert last_error is not None  # o laço executa ao menos uma vez
        raise last_error

    @staticmethod
    def _retryable_error(response: httpx.Response, path: str) -> WeatherProviderError:
        if response.status_code == 429:
            return RateLimitError(f"Limite de chamadas excedido (HTTP 429) em {path}.")
        return ProviderUnavailableError(
            f"Provedor indisponível (HTTP {response.status_code}) em {path}."
        )

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        raw = response.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            return min(max(float(raw), 0.0), _MAX_RETRY_AFTER_SECONDS)
        except ValueError:
            return None

    @staticmethod
    def _parse(response: httpx.Response, path: str) -> Any:
        status = response.status_code
        if status == 401:
            raise AuthenticationError(
                "Chave da OpenWeather inválida, ainda não ativada ou sem acesso ao produto "
                f"(HTTP 401) em {path}."
            )
        if status == 404:
            raise ResourceNotFoundError(f"Recurso não encontrado (HTTP 404): {path}.")
        if status >= 400:
            raise WeatherProviderError(f"Erro HTTP {status} em {path}.")
        try:
            return response.json()
        except ValueError as exc:
            raise PayloadError(f"Resposta não é um JSON válido em {path}.") from exc
