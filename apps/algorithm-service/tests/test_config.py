import pytest
from algorithm_service.config import Settings
from hypothesis import given
from hypothesis import strategies as st
from pydantic import SecretStr, ValidationError
from sqlalchemy.engine import make_url


@pytest.fixture(autouse=True)
def isolated_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGSSLMODE"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)


def test_database_password_is_required() -> None:
    with pytest.raises(ValidationError, match="pgpassword"):
        Settings()


def test_platform_environment_overrides_local_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {
        "PGHOST": "database.internal",
        "PGPORT": "5433",
        "PGDATABASE": "bound_database",
        "PGUSER": "bound_user",
        "PGPASSWORD": "private-value",
        "PGSSLMODE": "require",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    settings = Settings()
    url = settings.database_url
    assert url.drivername == "postgresql+psycopg"
    assert (url.host, url.port, url.database, url.username) == (
        "database.internal",
        5433,
        "bound_database",
        "bound_user",
    )
    assert url.password == "private-value"
    assert url.query["sslmode"] == "require"
    assert "private-value" not in repr(settings)
    assert "private-value" not in str(url)


@given(password=st.text(min_size=1))
def test_database_url_preserves_password_characters(password: str) -> None:
    url = Settings(pgpassword=SecretStr(password)).database_url
    assert make_url(url.render_as_string(hide_password=False)).password == password
