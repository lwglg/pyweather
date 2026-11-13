"""Injeção de dependências (FastAPI ``Depends``)."""

from typing import Annotated

from fastapi import Depends, Request

from pyweather_api.application.services import WeatherQueryService


def get_service(request: Request) -> WeatherQueryService:
    service: WeatherQueryService = request.app.state.service
    return service


Service = Annotated[WeatherQueryService, Depends(get_service)]
