import pytest
from pydantic import ValidationError

from pyweather_etl.config import Settings, get_settings
from pyweather_etl.domain.value_objects import Coordinates


def make(**overrides: object) -> Settings:
    return Settings.model_validate(overrides)


def test_valores_padrao(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("CITY_NAME", "CITY_LATITUDE", "CITY_LONGITUDE", "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)
    settings = make()

    assert settings.openweather_units == "metric"
    assert settings.openweather_lang == "pt_br"
    assert settings.location_spec.coordinates is None
    assert settings.location_spec.country == "BR"


def test_url_postgres_montada_com_segredo_escapado() -> None:
    settings = make(postgres_user="u", postgres_password="p@ss/word", postgres_host="db")
    url = settings.sqlalchemy_url

    assert not isinstance(url, str)
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "p@ss/word"
    assert "p@ss/word" not in url.render_as_string()  # a senha é mascarada/escapada
    assert url.host == "db"


def test_database_url_tem_precedencia() -> None:
    assert make(database_url="sqlite://").sqlalchemy_url == "sqlite://"


def test_coordenadas_explicitas() -> None:
    spec = make(city_latitude=-27.59, city_longitude=-48.54).location_spec
    assert spec.coordinates == Coordinates(-27.59, -48.54)


def test_coordenadas_devem_vir_em_par() -> None:
    with pytest.raises(ValidationError, match="CITY_LATITUDE"):
        make(city_latitude=1.0)


def test_chave_nao_aparece_no_repr() -> None:
    assert "segredo123" not in repr(make(openweather_api_key="segredo123"))


def test_get_settings_e_cacheado(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CITY_NAME", "Curitiba")
    assert get_settings() is get_settings()
    assert get_settings().city_name == "Curitiba"
    get_settings.cache_clear()
