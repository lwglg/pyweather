import pytest

from pyweather_etl.domain.errors import InvalidCoordinatesError
from pyweather_etl.domain.value_objects import Coordinates


def test_coordinates_validas() -> None:
    coordinates = Coordinates(-27.59, -48.54)
    assert coordinates.latitude == -27.59
    assert coordinates.longitude == -48.54


@pytest.mark.parametrize(
    ("latitude", "longitude", "message"),
    [
        (90.1, 0.0, "Latitude"),
        (-91.0, 0.0, "Latitude"),
        (0.0, 180.5, "Longitude"),
        (0.0, -181.0, "Longitude"),
    ],
)
def test_coordinates_invalidas(latitude: float, longitude: float, message: str) -> None:
    with pytest.raises(InvalidCoordinatesError, match=message):
        Coordinates(latitude, longitude)


def test_coordinates_sao_comparadas_por_valor() -> None:
    assert Coordinates(1.0, 2.0) == Coordinates(1.0, 2.0)
