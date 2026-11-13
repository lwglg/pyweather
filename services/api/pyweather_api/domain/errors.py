"""Erros do domínio da API."""


class DomainError(Exception):
    """Raiz da hierarquia de erros de domínio."""


class LocationNotFoundError(DomainError):
    def __init__(self, location_id: int) -> None:
        super().__init__(f"Local {location_id} não encontrado.")
        self.location_id = location_id


class NoDataError(DomainError):
    """O local existe, porém ainda não há dados extraídos para ele."""

    def __init__(self, location_id: int, what: str) -> None:
        super().__init__(f"Ainda não há {what} para o local {location_id}.")
        self.location_id = location_id


class InvalidFilterError(DomainError):
    """Combinação de filtros inválida (ex.: início posterior ao fim)."""
