from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from algorithm_service.config import Settings
from algorithm_service.database import create_database_engine
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration


def test_migration_lifecycle_against_isolated_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from testcontainers.community.postgres import PostgresContainer

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with PostgresContainer("postgres:18", driver="psycopg") as postgres:
        url = make_url(postgres.get_connection_url())
        bootstrap = create_engine(url)
        try:
            with bootstrap.begin() as connection:
                connection.execute(text("CREATE SCHEMA executions"))
        finally:
            bootstrap.dispose()

        for name, value in {
            "PGHOST": url.host,
            "PGPORT": str(url.port),
            "PGDATABASE": url.database,
            "PGUSER": url.username,
            "PGPASSWORD": url.password,
            "PGSSLMODE": "disable",
        }.items():
            assert value is not None
            monkeypatch.setenv(name, value)

        command.upgrade(config, "head")
        engine = create_database_engine(Settings())
        try:
            assert "execution" in inspect(engine).get_table_names(schema="executions")
            assert "alembic_version" not in inspect(engine).get_table_names(
                schema="public"
            )
            with engine.connect() as connection:
                assert (
                    connection.scalar(text("SELECT current_schema()")) == "executions"
                )

            statement = text("""
                INSERT INTO executions.execution
                  (id, algorithm_id, implementation_version, scenario_version_id,
                   input_snapshot, status, attempt)
                VALUES (:id, 'K01', 'test', :scenario, jsonb_build_object('n', 10), :status, :attempt)
            """)
            with engine.begin() as connection:
                for status in ("queued", "running", "succeeded", "failed", "cancelled"):
                    connection.execute(
                        statement,
                        {
                            "id": uuid4(),
                            "scenario": uuid4(),
                            "status": status,
                            "attempt": 0,
                        },
                    )
                for status, attempt in (
                    ("completed", 0),
                    ("invalid", 0),
                    ("queued", -1),
                ):
                    with pytest.raises(IntegrityError), connection.begin_nested():
                        connection.execute(
                            statement,
                            {
                                "id": uuid4(),
                                "scenario": uuid4(),
                                "status": status,
                                "attempt": attempt,
                            },
                        )

            command.upgrade(config, "head")
            with engine.connect() as connection:
                assert (
                    connection.scalar(text("SELECT count(*) FROM executions.execution"))
                    == 5
                )
                assert (
                    connection.scalar(
                        text("SELECT version_num FROM executions.alembic_version")
                    )
                    == "e6dbe344f903"
                )

            command.downgrade(config, "base")
            assert "execution" not in inspect(engine).get_table_names(
                schema="executions"
            )
            command.upgrade(config, "head")
            with engine.connect() as connection:
                assert (
                    connection.scalar(text("SELECT count(*) FROM executions.execution"))
                    == 0
                )
        finally:
            engine.dispose()
