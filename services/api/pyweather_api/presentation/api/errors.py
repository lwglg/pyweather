"""Mapeamento de erros de domínio para respostas HTTP."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from pyweather_api.domain.errors import (
    DomainError,
    InvalidFilterError,
    LocationNotFoundError,
    NoDataError,
)


_STATUS: dict[type[DomainError], int] = {
    LocationNotFoundError: status.HTTP_404_NOT_FOUND,
    NoDataError: status.HTTP_404_NOT_FOUND,
    InvalidFilterError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


async def _handle(_: Request, exc: Exception) -> JSONResponse:
    code = next(
        (value for kind, value in _STATUS.items() if isinstance(exc, kind)),
        status.HTTP_400_BAD_REQUEST,
    )
    return JSONResponse(status_code=code, content={"detail": str(exc)})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle)
