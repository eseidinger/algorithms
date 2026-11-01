from uuid import uuid4

import pytest
from algorithm_lab.fibonacci import fibonacci
from algorithm_service.repository import ExecutionRepository
from algorithm_service.worker import process_next_execution
from sqlalchemy import text
from sqlalchemy.engine import Engine

pytestmark = pytest.mark.integration


def test_worker_calculates_and_persists_fibonacci(engine: Engine) -> None:
    repository = ExecutionRepository(engine)
    created = repository.create_execution(
        algorithm_id="fibonacci.iterative",
        implementation_version="1",
        scenario_version_id=uuid4(),
        input_snapshot={"n": 10},
    )
    assert process_next_execution(repository) == "succeeded"
    stored = repository.get_execution(created.id)
    assert stored is not None
    assert stored.status == "succeeded"
    assert stored.result == {"value": 55}
    assert stored.attempt == 1
    assert stored.started_at is not None
    assert stored.finished_at is not None
    assert stored.finished_at >= stored.started_at
    assert stored.duration_ms is not None and stored.duration_ms >= 0
    assert stored.lease_until is None
    assert stored.error is None
    assert process_next_execution(repository) == "idle"


def test_worker_persists_calculation_failure(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = ExecutionRepository(engine)
    created = repository.create_execution(
        algorithm_id="fibonacci.iterative",
        implementation_version="1",
        scenario_version_id=uuid4(),
        input_snapshot={"n": 10},
    )

    def broken_calculation(n: int) -> int:
        raise RuntimeError("Computation failed")

    monkeypatch.setattr("algorithm_service.worker.fibonacci", broken_calculation)
    assert process_next_execution(repository) == "failed"
    stored = repository.get_execution(created.id)
    assert stored is not None
    assert stored.status == "failed"
    assert stored.result is None
    assert stored.error == "RuntimeError: Computation failed"
    assert stored.finished_at is not None
    assert stored.duration_ms is not None and stored.duration_ms >= 0
    assert stored.lease_until is None
    assert process_next_execution(repository) == "idle"


def test_worker_discards_expired_result_then_recovers_job(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = ExecutionRepository(engine)
    created = repository.create_execution(
        algorithm_id="fibonacci.iterative",
        implementation_version="1",
        scenario_version_id=uuid4(),
        input_snapshot={"n": 10},
    )

    def expire_during_calculation(n: int) -> int:
        value = fibonacci(n)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE executions.execution SET lease_until = clock_timestamp() - INTERVAL '1 second' WHERE id = :id"
                ),
                {"id": created.id},
            )
        return value

    monkeypatch.setattr("algorithm_service.worker.fibonacci", expire_during_calculation)
    assert process_next_execution(repository) == "discarded"
    stored = repository.get_execution(created.id)
    assert stored is not None
    assert stored.status == "running"
    assert stored.attempt == 1
    assert stored.result is None
    assert stored.error is None
    assert stored.finished_at is None

    monkeypatch.setattr("algorithm_service.worker.fibonacci", fibonacci)
    assert process_next_execution(repository) == "succeeded"
    recovered = repository.get_execution(created.id)
    assert recovered is not None
    assert recovered.status == "succeeded"
    assert recovered.attempt == 2
    assert recovered.result == {"value": 55}
