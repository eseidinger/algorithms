import pytest
from algorithm_service.config import Settings
from hypothesis import given
from hypothesis import strategies as st
from pydantic import SecretStr, ValidationError
from sqlalchemy.engine import make_url


@pytest.fixture(autouse=True)
def isolated_database_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "PGHOST",
        "PGPORT",
        "PGDATABASE",
        "PGUSER",
        "PGPASSWORD",
        "PGSSLMODE",
        "DATA_SERVICE_URL",
        "WORKER_POLL_INTERVAL",
        "WORKER_ERROR_RETRY_INTERVAL",
        "WORKER_LEASE_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)


def test_database_password_is_required() -> None:
    with pytest.raises(ValidationError, match="pgpassword"):
        Settings()


def test_data_service_url_defaults_to_local_spring() -> None:
    assert (
        Settings(pgpassword=SecretStr("test")).data_service_url
        == "http://localhost:8080"
    )


def test_data_service_url_can_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_SERVICE_URL", "http://data-service:8080")
    assert (
        Settings(pgpassword=SecretStr("test")).data_service_url
        == "http://data-service:8080"
    )


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


def test_worker_defaults_and_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(pgpassword=SecretStr("test"))
    assert settings.worker_poll_interval == 1.0
    assert settings.worker_error_retry_interval == 5.0
    assert settings.worker_lease_seconds == 30
    monkeypatch.setenv("WORKER_POLL_INTERVAL", "0.25")
    monkeypatch.setenv("WORKER_ERROR_RETRY_INTERVAL", "2.5")
    monkeypatch.setenv("WORKER_LEASE_SECONDS", "60")
    configured = Settings(pgpassword=SecretStr("test"))
    assert configured.worker_poll_interval == 0.25
    assert configured.worker_error_retry_interval == 2.5
    assert configured.worker_lease_seconds == 60


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("WORKER_POLL_INTERVAL", "0"),
        ("WORKER_POLL_INTERVAL", "-1"),
        ("WORKER_POLL_INTERVAL", "nan"),
        ("WORKER_POLL_INTERVAL", "inf"),
        ("WORKER_ERROR_RETRY_INTERVAL", "0"),
        ("WORKER_ERROR_RETRY_INTERVAL", "-1"),
        ("WORKER_ERROR_RETRY_INTERVAL", "nan"),
        ("WORKER_ERROR_RETRY_INTERVAL", "inf"),
        ("WORKER_LEASE_SECONDS", "0"),
        ("WORKER_LEASE_SECONDS", "-1"),
    ],
)
def test_worker_rejects_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings(pgpassword=SecretStr("test"))
