"""Erros do domínio e das portas do ETL."""


class PyWeatherError(Exception):
    """Raiz da hierarquia de erros do ETL."""


class InvalidCoordinatesError(PyWeatherError, ValueError):
    """Latitude/longitude fora dos limites geográficos válidos."""


class ConfigurationError(PyWeatherError):
    """Configuração ausente ou inválida (ex.: chave da API não informada)."""


class WeatherProviderError(PyWeatherError):
    """Falha genérica na comunicação com o provedor de dados climáticos."""


class AuthenticationError(WeatherProviderError):
    """Chave de API inválida ou sem acesso ao produto (HTTP 401)."""


class RateLimitError(WeatherProviderError):
    """Limite de chamadas excedido (HTTP 429) mesmo após novas tentativas."""


class ProviderUnavailableError(WeatherProviderError):
    """Provedor indisponível (erros 5xx ou falhas de rede) mesmo após novas tentativas."""


class ResourceNotFoundError(WeatherProviderError):
    """Recurso inexistente no provedor (HTTP 404)."""


class LocationNotFoundError(WeatherProviderError):
    """A cidade informada não foi encontrada pelo serviço de geocodificação."""


class PayloadError(WeatherProviderError):
    """Resposta do provedor fora do formato esperado."""
