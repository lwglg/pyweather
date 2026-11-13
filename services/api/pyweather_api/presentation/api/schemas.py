"""Esquemas HTTP (Pydantic). Nomes de campos em inglês; descrições (OpenAPI) em português."""

from datetime import UTC, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from pyweather_api.domain.models import (
    AlertFilter,
    CurrentFilter,
    DailyFilter,
    HourlyFilter,
    LocationFilter,
    Pagination,
    SortOrder,
    TimeRange,
)


# --- Respostas ---------------------------------------------------------------------------------
class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LocationOut(_Out):
    id: int = Field(description="Identificador do local.", examples=[1])
    name: str = Field(description="Nome da cidade.", examples=["Florianópolis"])
    state: str | None = Field(
        description="Estado/região, quando disponível.", examples=["Santa Catarina"]
    )
    country: str = Field(description="Código ISO 3166 do país.", examples=["BR"])
    latitude: float = Field(description="Latitude em graus decimais.", examples=[-27.5954])
    longitude: float = Field(description="Longitude em graus decimais.", examples=[-48.548])
    timezone: str | None = Field(description="Fuso horário IANA.", examples=["America/Sao_Paulo"])
    timezone_offset: int | None = Field(
        description="Deslocamento do fuso em relação a UTC, em segundos.", examples=[-10800]
    )


class ConditionOut(_Out):
    code: int | None = Field(description="Código da condição (OpenWeather).", examples=[500])
    main: str | None = Field(description="Grupo da condição.", examples=["Rain"])
    description: str | None = Field(description="Descrição localizada.", examples=["chuva leve"])
    icon: str | None = Field(description="Código do ícone.", examples=["10d"])


class CurrentWeatherOut(_Out):
    location_id: int = Field(description="Identificador do local.")
    observed_at: datetime = Field(description="Instante da observação (UTC).")
    temperature: float = Field(description="Temperatura (°C no sistema métrico).")
    feels_like: float = Field(description="Sensação térmica.")
    pressure: int = Field(description="Pressão atmosférica ao nível do mar (hPa).")
    humidity: int = Field(description="Umidade relativa (%).")
    dew_point: float | None = Field(description="Ponto de orvalho.")
    uvi: float | None = Field(description="Índice UV.")
    clouds: int | None = Field(description="Nebulosidade (%).")
    visibility: int | None = Field(description="Visibilidade (m).")
    wind_speed: float | None = Field(description="Velocidade do vento (m/s).")
    wind_deg: int | None = Field(description="Direção do vento (graus).")
    wind_gust: float | None = Field(description="Rajada de vento (m/s).")
    rain_1h: float | None = Field(description="Chuva na última hora (mm).")
    snow_1h: float | None = Field(description="Neve na última hora (mm).")
    condition: ConditionOut = Field(description="Condição meteorológica.")
    sunrise: datetime | None = Field(description="Nascer do sol (UTC).")
    sunset: datetime | None = Field(description="Pôr do sol (UTC).")
    fetched_at: datetime = Field(description="Instante da última extração do registro (UTC).")


class HourlyForecastOut(_Out):
    location_id: int = Field(description="Identificador do local.")
    forecast_at: datetime = Field(description="Hora a que a previsão se refere (UTC).")
    temperature: float = Field(description="Temperatura prevista.")
    feels_like: float = Field(description="Sensação térmica prevista.")
    pressure: int = Field(description="Pressão (hPa).")
    humidity: int = Field(description="Umidade relativa (%).")
    dew_point: float | None = Field(description="Ponto de orvalho.")
    uvi: float | None = Field(description="Índice UV.")
    clouds: int | None = Field(description="Nebulosidade (%).")
    visibility: int | None = Field(description="Visibilidade (m).")
    wind_speed: float | None = Field(description="Velocidade do vento (m/s).")
    wind_deg: int | None = Field(description="Direção do vento (graus).")
    wind_gust: float | None = Field(description="Rajada de vento (m/s).")
    rain_1h: float | None = Field(description="Chuva prevista na hora (mm).")
    snow_1h: float | None = Field(description="Neve prevista na hora (mm).")
    pop: float | None = Field(description="Probabilidade de precipitação (0 a 1).")
    condition: ConditionOut = Field(description="Condição meteorológica.")
    fetched_at: datetime = Field(description="Instante da última extração do registro (UTC).")


class DailyForecastOut(_Out):
    location_id: int = Field(description="Identificador do local.")
    forecast_at: datetime = Field(description="Dia a que a previsão se refere (UTC).")
    temp_day: float | None = Field(description="Temperatura diurna.")
    temp_min: float | None = Field(description="Temperatura mínima do dia.")
    temp_max: float | None = Field(description="Temperatura máxima do dia.")
    temp_night: float | None = Field(description="Temperatura noturna.")
    temp_eve: float | None = Field(description="Temperatura ao entardecer.")
    temp_morn: float | None = Field(description="Temperatura pela manhã.")
    feels_like_day: float | None = Field(description="Sensação térmica diurna.")
    feels_like_night: float | None = Field(description="Sensação térmica noturna.")
    feels_like_eve: float | None = Field(description="Sensação térmica ao entardecer.")
    feels_like_morn: float | None = Field(description="Sensação térmica pela manhã.")
    pressure: int | None = Field(description="Pressão (hPa).")
    humidity: int | None = Field(description="Umidade relativa (%).")
    dew_point: float | None = Field(description="Ponto de orvalho.")
    uvi: float | None = Field(description="Índice UV máximo.")
    clouds: int | None = Field(description="Nebulosidade (%).")
    wind_speed: float | None = Field(description="Velocidade do vento (m/s).")
    wind_deg: int | None = Field(description="Direção do vento (graus).")
    wind_gust: float | None = Field(description="Rajada de vento (m/s).")
    rain: float | None = Field(description="Volume de chuva previsto (mm).")
    snow: float | None = Field(description="Volume de neve previsto (mm).")
    pop: float | None = Field(description="Probabilidade de precipitação (0 a 1).")
    condition: ConditionOut = Field(description="Condição meteorológica.")
    sunrise: datetime | None = Field(description="Nascer do sol (UTC).")
    sunset: datetime | None = Field(description="Pôr do sol (UTC).")
    moonrise: datetime | None = Field(description="Nascer da lua (UTC).")
    moonset: datetime | None = Field(description="Pôr da lua (UTC).")
    moon_phase: float | None = Field(description="Fase da lua (0 e 1 = lua nova; 0,5 = lua cheia).")
    fetched_at: datetime = Field(description="Instante da última extração do registro (UTC).")


class AlertDescriptionOut(_Out):
    language: str = Field(description="Idioma do texto.", examples=["pt-BR"])
    description: str = Field(description="Texto do alerta no idioma indicado.")


class WeatherAlertOut(_Out):
    location_id: int = Field(description="Identificador do local.")
    alert_id: str = Field(description="Identificador do alerta no provedor.")
    sender_name: str = Field(description="Agência emissora.", examples=["INMET"])
    event: str = Field(description="Tipo do evento.", examples=["Tempestade"])
    starts_at: datetime = Field(description="Início da vigência (UTC).")
    ends_at: datetime = Field(description="Fim da vigência (UTC).")
    descriptions: tuple[AlertDescriptionOut, ...] = Field(description="Textos por idioma.")
    tags: tuple[str, ...] = Field(description="Categorias do alerta.")
    fetched_at: datetime = Field(description="Instante da última extração do registro (UTC).")


class PageOut[T](BaseModel):
    items: list[T] = Field(description="Itens da página.")
    total: int = Field(description="Total de itens que satisfazem os filtros.", examples=[120])
    limit: int = Field(description="Tamanho máximo da página solicitada.", examples=[50])
    offset: int = Field(description="Posição inicial da página.", examples=[0])


class ErrorOut(BaseModel):
    detail: str = Field(
        description="Mensagem de erro legível.", examples=["Local 99 não encontrado."]
    )


class HealthOut(BaseModel):
    status: str = Field(description="Estado do serviço.", examples=["ok"])


# --- Parâmetros de consulta -------------------------------------------------------------------
def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class _Query(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PageQuery(_Query):
    limit: int = Field(default=50, ge=1, le=200, description="Itens por página (1 a 200).")
    offset: int = Field(default=0, ge=0, description="Quantidade de itens a pular.")

    def to_domain(self) -> Pagination:
        return Pagination(limit=self.limit, offset=self.offset)


class _PeriodQuery(PageQuery):
    start: datetime | None = Field(
        default=None,
        description="Início do período (inclusivo). Sem fuso horário, assume-se UTC.",
        examples=["2026-11-12T00:00:00Z"],
    )
    end: datetime | None = Field(
        default=None, description="Fim do período (inclusivo). Sem fuso horário, assume-se UTC."
    )
    order: SortOrder = Field(default=SortOrder.ASC, description="Ordenação cronológica.")

    def period(self) -> TimeRange:
        return TimeRange(start=_utc(self.start), end=_utc(self.end))


class LocationQuery(PageQuery):
    name: str | None = Field(
        default=None, description="Trecho do nome da cidade (sem distinção de maiúsculas)."
    )
    state: str | None = Field(default=None, description="Trecho do nome do estado/região.")
    country: str | None = Field(default=None, description="Código do país (ex.: BR).", max_length=8)

    def filter(self) -> LocationFilter:
        return LocationFilter(name=self.name, state=self.state, country=self.country)


class CurrentQuery(_PeriodQuery):
    order: SortOrder = Field(default=SortOrder.DESC, description="Ordenação cronológica.")
    min_temperature: float | None = Field(default=None, description="Temperatura mínima.")
    max_temperature: float | None = Field(default=None, description="Temperatura máxima.")
    min_humidity: int | None = Field(default=None, ge=0, le=100, description="Umidade mínima (%).")
    max_humidity: int | None = Field(default=None, ge=0, le=100, description="Umidade máxima (%).")
    condition: str | None = Field(
        default=None, description="Trecho do grupo ou da descrição da condição (ex.: chuva, Clear)."
    )

    def filter(self) -> CurrentFilter:
        return CurrentFilter(
            period=self.period(),
            min_temperature=self.min_temperature,
            max_temperature=self.max_temperature,
            min_humidity=self.min_humidity,
            max_humidity=self.max_humidity,
            condition=self.condition,
            order=self.order,
        )


class HourlyQuery(_PeriodQuery):
    min_temperature: float | None = Field(default=None, description="Temperatura mínima.")
    max_temperature: float | None = Field(default=None, description="Temperatura máxima.")
    min_pop: float | None = Field(
        default=None, ge=0, le=1, description="Probabilidade mínima de precipitação (0 a 1)."
    )
    condition: str | None = Field(
        default=None, description="Trecho do grupo ou da descrição da condição."
    )

    def filter(self) -> HourlyFilter:
        return HourlyFilter(
            period=self.period(),
            min_temperature=self.min_temperature,
            max_temperature=self.max_temperature,
            min_pop=self.min_pop,
            condition=self.condition,
            order=self.order,
        )


class DailyQuery(_PeriodQuery):
    min_temperature: float | None = Field(
        default=None, description="Considera dias cuja temperatura mínima seja ≥ ao valor."
    )
    max_temperature: float | None = Field(
        default=None, description="Considera dias cuja temperatura máxima seja ≤ ao valor."
    )
    min_pop: float | None = Field(
        default=None, ge=0, le=1, description="Probabilidade mínima de precipitação (0 a 1)."
    )
    condition: str | None = Field(
        default=None, description="Trecho do grupo ou da descrição da condição."
    )

    def filter(self) -> DailyFilter:
        return DailyFilter(
            period=self.period(),
            min_temperature=self.min_temperature,
            max_temperature=self.max_temperature,
            min_pop=self.min_pop,
            condition=self.condition,
            order=self.order,
        )


class AlertQuery(PageQuery):
    event: str | None = Field(default=None, description="Trecho do tipo do evento.")
    sender: str | None = Field(default=None, description="Trecho do nome da agência emissora.")
    active_at: AwareDatetime | None = Field(
        default=None,
        description="Retorna somente alertas vigentes neste instante (requer fuso horário).",
        examples=["2026-11-12T15:00:00Z"],
    )
    order: SortOrder = Field(
        default=SortOrder.DESC, description="Ordenação por início da vigência."
    )

    def filter(self) -> AlertFilter:
        return AlertFilter(
            event=self.event, sender=self.sender, active_at=_utc(self.active_at), order=self.order
        )
