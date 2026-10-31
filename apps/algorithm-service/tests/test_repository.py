from uuid import uuid4

import pytest
from algorithm_service.config import Settings
from algorithm_service.database import create_database_engine
from algorithm_service.repository import ExecutionRepository
from pydantic import JsonValue
from sqlalchemy import text
from sqlalchemy.exc import DataError

pytestmark = pytest.mark.integration


def test_create_commits_snapshot_and_defaults_for_independent_reader(
    database_settings: Settings,
) -> None:
    scenario_id = uuid4()
    snapshot: dict[str, JsonValue] = {
        "n": 10,
        "metadata": {"label": "DNA & Grüße", "flags": [True, None, 1.5]},
    }
    writer_engine = create_database_engine(database_settings)
    try:
        created = ExecutionRepository(writer_engine).create_execution(
            algorithm_id="fibonacci.iterative",
            implementation_version="1",
            scenario_version_id=scenario_id,
            input_snapshot=snapshot,
        )
    finally:
        writer_engine.dispose()

    assert created.algorithm_id == "fibonacci.iterative"
    assert created.implementation_version == "1"
    assert created.scenario_version_id == scenario_id
    assert created.input_snapshot == snapshot
    assert created.status == "queued"
    assert created.attempt == 0
    assert created.created_at.tzinfo is not None
    assert created.lease_until is None
    assert created.result is None
    assert created.error is None
    assert created.duration_ms is None
    assert created.started_at is None
    assert created.finished_at is None

    snapshot["n"] = 20
    reader_engine = create_database_engine(database_settings)
    try:
        loaded = ExecutionRepository(reader_engine).get_execution(created.id)
        assert loaded == created
        assert loaded.input_snapshot["n"] == 10
    finally:
        reader_engine.dispose()


def test_unknown_execution_returns_none(database_settings: Settings) -> None:
    engine = create_database_engine(database_settings)
    try:
        assert ExecutionRepository(engine).get_execution(uuid4()) is None
    finally:
        engine.dispose()


def test_failed_insert_does_not_persist_a_job_and_repository_remains_usable(
    database_settings: Settings,
) -> None:
    engine = create_database_engine(database_settings)
    repository = ExecutionRepository(engine)
    try:
        with pytest.raises(DataError):
            repository.create_execution(
                algorithm_id="fibonacci.iterative",
                implementation_version="x" * 65,
                scenario_version_id=uuid4(),
                input_snapshot={"n": 10},
            )
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT count(*) FROM executions.execution"))
                == 0
            )

        created = repository.create_execution(
            algorithm_id="fibonacci.iterative",
            implementation_version="1",
            scenario_version_id=uuid4(),
            input_snapshot={"n": 10},
        )
        assert repository.get_execution(created.id) == created
    finally:
        engine.dispose()
