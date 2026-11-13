from fastapi import APIRouter, HTTPException, status

from pyweather_api.presentation.api.dependencies import Service
from pyweather_api.presentation.api.schemas import ErrorOut, HealthOut


router = APIRouter(tags=["Saúde"])


@router.get(
    "/health",
    response_model=HealthOut,
    summary="Verifica se o serviço está no ar",
    description=(
        "*Liveness*: responde `ok` sempre que o processo está de pé, sem consultar o banco."
    ),
)
def liveness() -> HealthOut:
    return HealthOut(status="ok")


@router.get(
    "/health/ready",
    response_model=HealthOut,
    responses={503: {"model": ErrorOut, "description": "Banco de dados indisponível."}},
    summary="Verifica se o serviço está pronto para receber tráfego",
    description="*Readiness*: confirma que o banco de dados PostgreSQL responde.",
)
def readiness(service: Service) -> HealthOut:
    if not service.is_healthy():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Banco de dados indisponível.")
    return HealthOut(status="ok")
