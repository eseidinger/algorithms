from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from algorithm_service.config import Settings
from algorithm_service.database import create_database_engine
from algorithm_service.models import Execution
from algorithm_service.repository import ExecutionRepository
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

pytestmark = pytest.mark.integration


@pytest.fixture
def engine(database_settings: Settings) -> Iterator[Engine]:
    engine = create_database_engine(database_settings)
    try:
        yield engine
    finally:
        engine.dispose()


def create_job(repository: ExecutionRepository) -> Execution:
    return repository.create_execution(
        algorithm_id="fibonacci.iterative",
        implementation_version="1",
        scenario_version_id=uuid4(),
        input_snapshot={"n": 10},
    )


def test_empty_queue_and_invalid_lease_duration(engine: Engine) -> None:
    repository = ExecutionRepository(engine)
    assert repository.reserve_execution() is None
    for duration in (0, -1):
        with pytest.raises(ValueError, match="positive"):
            repository.reserve_execution(lease_seconds=duration)


def test_reservation_is_committed_and_expired_lease_can_be_recovered(
    engine: Engine,
) -> None:
    repository = ExecutionRepository(engine)
    created = create_job(repository)

    reserved = repository.reserve_execution(lease_seconds=60)
    assert reserved is not None
    assert reserved.id == created.id
    assert reserved.status == "running"
    assert reserved.attempt == 1
    assert reserved.started_at is not None
    assert reserved.lease_until == reserved.started_at + timedelta(seconds=60)
    assert ExecutionRepository(engine).get_execution(created.id) == reserved
    assert repository.reserve_execution() is None

    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE executions.execution
                SET lease_until = CURRENT_TIMESTAMP - INTERVAL '1 second',
                    finished_at = CURRENT_TIMESTAMP,
                    result = jsonb_build_object('value', 123),
                    error = 'previous attempt',
                    duration_ms = 1.0
                WHERE id = :id
            """),
            {"id": created.id},
        )

    recovered = repository.reserve_execution()
    assert recovered is not None
    assert recovered.id == created.id
    assert recovered.status == "running"
    assert recovered.attempt == 2
    assert recovered.started_at is not None
    assert recovered.started_at >= reserved.started_at
    assert recovered.lease_until == recovered.started_at + timedelta(seconds=30)
    assert recovered.finished_at is None
    assert recovered.result is None
    assert recovered.error is None
    assert recovered.duration_ms is None


def test_reservation_skips_locked_job_without_waiting(engine: Engine) -> None:
    repository = ExecutionRepository(engine)
    first = create_job(repository)
    second = create_job(repository)

    with engine.begin() as connection:
        connection.execute(
            text("SELECT id FROM executions.execution WHERE id = :id FOR UPDATE"),
            {"id": first.id},
        ).one()

        # Bound a missing SKIP LOCKED regression instead of hanging the test.
        limited_engine = create_engine(
            engine.url,
            connect_args={"options": "-cstatement_timeout=2000"},
        )
        try:
            reserved = ExecutionRepository(limited_engine).reserve_execution()
        finally:
            limited_engine.dispose()

        assert reserved is not None
        assert reserved.id == second.id
        assert repository.reserve_execution() is None

    reserved = repository.reserve_execution()
    assert reserved is not None
    assert reserved.id == first.id


def test_terminal_jobs_and_running_job_without_expired_lease_are_not_reserved(
    engine: Engine,
) -> None:
    repository = ExecutionRepository(engine)
    for status in ("succeeded", "failed", "cancelled", "running"):
        job = create_job(repository)
        with engine.begin() as connection:
            connection.execute(
                text("""
                    UPDATE executions.execution
                    SET status = :status,
                        lease_until = CASE WHEN :without_lease THEN NULL
                            ELSE CURRENT_TIMESTAMP - INTERVAL '1 second' END
                    WHERE id = :id
                """),
                {"status": status, "without_lease": status == "running", "id": job.id},
            )
    assert repository.reserve_execution() is None


def test_concurrent_workers_cannot_reserve_same_job(engine: Engine) -> None:
    repository = ExecutionRepository(engine)
    created = create_job(repository)
    barrier = Barrier(2)

    def reserve() -> Execution | None:
        barrier.wait(timeout=5)
        return ExecutionRepository(engine).reserve_execution()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(reserve) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]

    reserved = [result for result in results if result is not None]
    assert len(reserved) == 1
    assert reserved[0].id == created.id
    assert reserved[0].attempt == 1
