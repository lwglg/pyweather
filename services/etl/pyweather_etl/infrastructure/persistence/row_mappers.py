"""Entidades de domínio → linhas das tabelas relacionais."""

from datetime import datetime

from pyweather_etl.domain.entities import (
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    WeatherAlert,
)
from pyweather_etl.infrastructure.persistence.models import (
    CurrentWeatherModel,
    DailyForecastModel,
    HourlyForecastModel,
    WeatherAlertModel,
)


def to_current_row(
    location_id: int, weather: CurrentWeather, fetched_at: datetime
) -> CurrentWeatherModel:
    condition = weather.condition
    return CurrentWeatherModel(
        location_id=location_id,
        observed_at=weather.observed_at,
        temperature=weather.temperature,
        feels_like=weather.feels_like,
        pressure=weather.pressure,
        humidity=weather.humidity,
        dew_point=weather.dew_point,
        uvi=weather.uvi,
        clouds=weather.clouds,
        visibility=weather.visibility,
        wind_speed=weather.wind.speed,
        wind_deg=weather.wind.direction,
        wind_gust=weather.wind.gust,
        rain_1h=weather.precipitation.rain,
        snow_1h=weather.precipitation.snow,
        condition_code=condition.code if condition else None,
        condition_main=condition.main if condition else None,
        condition_description=condition.description if condition else None,
        condition_icon=condition.icon if condition else None,
        sunrise=weather.sunrise,
        sunset=weather.sunset,
        fetched_at=fetched_at,
    )


def to_hourly_row(
    location_id: int, forecast: HourlyForecast, fetched_at: datetime
) -> HourlyForecastModel:
    condition = forecast.condition
    return HourlyForecastModel(
        location_id=location_id,
        forecast_at=forecast.forecast_at,
        temperature=forecast.temperature,
        feels_like=forecast.feels_like,
        pressure=forecast.pressure,
        humidity=forecast.humidity,
        dew_point=forecast.dew_point,
        uvi=forecast.uvi,
        clouds=forecast.clouds,
        visibility=forecast.visibility,
        wind_speed=forecast.wind.speed,
        wind_deg=forecast.wind.direction,
        wind_gust=forecast.wind.gust,
        rain_1h=forecast.precipitation.rain,
        snow_1h=forecast.precipitation.snow,
        pop=forecast.precipitation.probability,
        condition_code=condition.code if condition else None,
        condition_main=condition.main if condition else None,
        condition_description=condition.description if condition else None,
        condition_icon=condition.icon if condition else None,
        fetched_at=fetched_at,
    )


def to_daily_row(
    location_id: int, forecast: DailyForecast, fetched_at: datetime
) -> DailyForecastModel:
    condition = forecast.condition
    return DailyForecastModel(
        location_id=location_id,
        forecast_at=forecast.forecast_at,
        temp_day=forecast.temperature.day,
        temp_min=forecast.temperature.min,
        temp_max=forecast.temperature.max,
        temp_night=forecast.temperature.night,
        temp_eve=forecast.temperature.evening,
        temp_morn=forecast.temperature.morning,
        feels_like_day=forecast.feels_like.day,
        feels_like_night=forecast.feels_like.night,
        feels_like_eve=forecast.feels_like.evening,
        feels_like_morn=forecast.feels_like.morning,
        pressure=forecast.pressure,
        humidity=forecast.humidity,
        dew_point=forecast.dew_point,
        uvi=forecast.uvi,
        clouds=forecast.clouds,
        wind_speed=forecast.wind.speed,
        wind_deg=forecast.wind.direction,
        wind_gust=forecast.wind.gust,
        rain=forecast.precipitation.rain,
        snow=forecast.precipitation.snow,
        pop=forecast.precipitation.probability,
        condition_code=condition.code if condition else None,
        condition_main=condition.main if condition else None,
        condition_description=condition.description if condition else None,
        condition_icon=condition.icon if condition else None,
        sunrise=forecast.sunrise,
        sunset=forecast.sunset,
        moonrise=forecast.moonrise,
        moonset=forecast.moonset,
        moon_phase=forecast.moon_phase,
        fetched_at=fetched_at,
    )


def to_alert_row(location_id: int, alert: WeatherAlert, fetched_at: datetime) -> WeatherAlertModel:
    return WeatherAlertModel(
        location_id=location_id,
        alert_id=alert.alert_id,
        sender_name=alert.sender_name,
        event=alert.event,
        starts_at=alert.starts_at,
        ends_at=alert.ends_at,
        descriptions=[{"language": d.language, "description": d.text} for d in alert.descriptions],
        tags=list(alert.tags),
        fetched_at=fetched_at,
    )
