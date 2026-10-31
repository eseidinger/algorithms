from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from algorithm_service.config import Settings
from pydantic import SecretStr
from sqlalchemy import create_engine, text


@pytest.fixture
def database_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[Settings]:
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("postgres:18", driver="psycopg") as postgres:
        bootstrap = create_engine(postgres.get_connection_url())
        try:
            with bootstrap.begin() as connection:
                connection.execute(text("CREATE SCHEMA executions"))
            url = bootstrap.url
            settings = Settings(
                pghost=str(url.host),
                pgport=int(url.port or 5432),
                pgdatabase=str(url.database),
                pguser=str(url.username),
                pgpassword=SecretStr(str(url.password)),
                pgsslmode="disable",
            )
        finally:
            bootstrap.dispose()

        for name in ("pghost", "pgport", "pgdatabase", "pguser", "pgsslmode"):
            monkeypatch.setenv(name.upper(), str(getattr(settings, name)))
        monkeypatch.setenv("PGPASSWORD", settings.pgpassword.get_secret_value())
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(config, "head")
        yield settings
