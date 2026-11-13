from typing import Annotated, Any

from fastapi import APIRouter, Path, Query

from pyweather_api.presentation.api.dependencies import Service
from pyweather_api.presentation.api.schemas import (
    AlertQuery,
    CurrentQuery,
    CurrentWeatherOut,
    DailyForecastOut,
    DailyQuery,
    ErrorOut,
    HourlyForecastOut,
    HourlyQuery,
    LocationOut,
    LocationQuery,
    PageOut,
    WeatherAlertOut,
)


router = APIRouter(prefix="/v1/locations", tags=["Locais e dados climáticos"])

LocationId = Annotated[int, Path(ge=1, description="Identificador do local.", examples=[1])]
NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorOut, "description": "Local inexistente ou sem dados extraídos."}
}
INVALID: dict[int | str, dict[str, Any]] = {
    422: {"model": ErrorOut, "description": "Filtros inválidos ou inconsistentes."}
}


@router.get(
    "",
    response_model=PageOut[LocationOut],
    summary="Lista os locais monitorados",
    description="Retorna as cidades para as quais o ETL já extraiu dados, com filtros por nome, "
    "estado e país. A ordenação é alfabética por nome.",
)
def list_locations(
    service: Service, query: Annotated[LocationQuery, Query()]
) -> PageOut[LocationOut]:
    page = service.list_locations(query.filter(), query.to_domain())
    return PageOut[LocationOut].model_validate(page, from_attributes=True)


@router.get(
    "/{location_id}",
    response_model=LocationOut,
    responses=NOT_FOUND,
    summary="Detalha um local",
)
def get_location(service: Service, location_id: LocationId) -> LocationOut:
    return LocationOut.model_validate(service.get_location(location_id))


@router.get(
    "/{location_id}/current",
    response_model=CurrentWeatherOut,
    responses=NOT_FOUND,
    summary="Condições climáticas mais recentes",
    description="Retorna a observação mais recente já extraída para o local.",
)
def latest_current(service: Service, location_id: LocationId) -> CurrentWeatherOut:
    return CurrentWeatherOut.model_validate(service.latest_current(location_id))


@router.get(
    "/{location_id}/current/history",
    response_model=PageOut[CurrentWeatherOut],
    responses={**NOT_FOUND, **INVALID},
    summary="Histórico de condições atuais",
    description="Série das observações acumuladas pelo ETL, com filtros por período, "
    "temperatura, umidade e condição. Por padrão, da mais recente para a mais antiga.",
)
def current_history(
    service: Service, location_id: LocationId, query: Annotated[CurrentQuery, Query()]
) -> PageOut[CurrentWeatherOut]:
    page = service.list_current(location_id, query.filter(), query.to_domain())
    return PageOut[CurrentWeatherOut].model_validate(page, from_attributes=True)


@router.get(
    "/{location_id}/forecast/hourly",
    response_model=PageOut[HourlyForecastOut],
    responses={**NOT_FOUND, **INVALID},
    summary="Previsão horária",
    description="Previsões em passos curtos (3 horas, no plano gratuito da OpenWeather), com "
    "filtros por período, temperatura, probabilidade de precipitação e condição.",
)
def hourly_forecast(
    service: Service, location_id: LocationId, query: Annotated[HourlyQuery, Query()]
) -> PageOut[HourlyForecastOut]:
    page = service.list_hourly(location_id, query.filter(), query.to_domain())
    return PageOut[HourlyForecastOut].model_validate(page, from_attributes=True)


@router.get(
    "/{location_id}/forecast/daily",
    response_model=PageOut[DailyForecastOut],
    responses={**NOT_FOUND, **INVALID},
    summary="Previsão diária",
    description="Resumo diário derivado dos passos de 3 horas (mínima, máxima, média, chuva "
    "acumulada e condição predominante), com filtros por período, temperatura, probabilidade "
    "de precipitação e condição. Os campos de lua, sol e por período do dia podem vir nulos.",
)
def daily_forecast(
    service: Service, location_id: LocationId, query: Annotated[DailyQuery, Query()]
) -> PageOut[DailyForecastOut]:
    page = service.list_daily(location_id, query.filter(), query.to_domain())
    return PageOut[DailyForecastOut].model_validate(page, from_attributes=True)


@router.get(
    "/{location_id}/alerts",
    response_model=PageOut[WeatherAlertOut],
    responses=NOT_FOUND,
    summary="Alertas meteorológicos",
    description="Alertas emitidos por agências nacionais, com filtros por evento, emissor "
    "e vigência (`active_at`). O plano gratuito da OpenWeather não fornece alertas; a lista "
    "permanece vazia, a menos que o banco seja alimentado por outra fonte.",
)
def alerts(
    service: Service, location_id: LocationId, query: Annotated[AlertQuery, Query()]
) -> PageOut[WeatherAlertOut]:
    page = service.list_alerts(location_id, query.filter(), query.to_domain())
    return PageOut[WeatherAlertOut].model_validate(page, from_attributes=True)
