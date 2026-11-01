from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import monotonic, sleep
from uuid import UUID, uuid4

import pytest
from algorithm_service.models import Execution
from algorithm_service.repository import ExecutionRepository
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

pytestmark = pytest.mark.integration


def create_reserved(repository: ExecutionRepository) -> Execution:
    created = repository.create_execution(
        algorithm_id="fibonacci.iterative",
        implementation_version="1",
        scenario_version_id=uuid4(),
        input_snapshot={"n": 10},
    )
    reserved = repository.reserve_execution(lease_seconds=60)
    assert reserved is not None
    assert reserved.id == created.id
    return reserved


def finish(
    repository: ExecutionRepository, id: UUID, attempt: int, succeed: bool
) -> bool:
    if succeed:
        return repository.complete_execution(
            id, attempt=attempt, result={"value": 55}, duration_ms=0.5
        )
    return repository.fail_execution(
        id, attempt=attempt, error="Calculation failed", duration_ms=0.5
    )


def expire(engine: Engine, id: UUID) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE executions.execution
                SET lease_until = clock_timestamp() - INTERVAL '1 second'
                WHERE id = :id
            """),
            {"id": id},
        )


def test_valid_success_and_failure_are_committed_and_cannot_be_overwritten(
    engine: Engine,
) -> None:
    repository = ExecutionRepository(engine)
    for succeed in (True, False):
        reserved = create_reserved(repository)
        assert finish(repository, reserved.id, reserved.attempt, succeed) is True
        completed = ExecutionRepository(engine).get_execution(reserved.id)
        assert completed is not None
        assert completed.status == ("succeeded" if succeed else "failed")
        assert completed.result == ({"value": 55} if succeed else None)
        assert completed.error == (None if succeed else "Calculation failed")
        assert completed.duration_ms == 0.5
        assert completed.finished_at is not None
        assert completed.started_at == reserved.started_at
        assert completed.attempt == reserved.attempt
        assert completed.lease_until is None
        assert completed.input_snapshot == reserved.input_snapshot

        for repeated_success in (True, False):
            assert (
                finish(repository, reserved.id, reserved.attempt, repeated_success)
                is False
            )
            assert repository.get_execution(reserved.id) == completed


def test_expired_lease_rejects_both_outcomes_without_reassignment(
    engine: Engine,
) -> None:
    repository = ExecutionRepository(engine)
    reserved = create_reserved(repository)
    expire(engine, reserved.id)
    before = repository.get_execution(reserved.id)
    for succeed in (True, False):
        assert finish(repository, reserved.id, reserved.attempt, succeed) is False
        assert repository.get_execution(reserved.id) == before


def test_obsolete_attempt_cannot_overwrite_new_reservation(engine: Engine) -> None:
    repository = ExecutionRepository(engine)
    first = create_reserved(repository)
    expire(engine, first.id)
    second = repository.reserve_execution(lease_seconds=60)
    assert second is not None
    assert second.attempt == first.attempt + 1
    for succeed in (True, False):
        assert finish(repository, first.id, first.attempt, succeed) is False
        assert repository.get_execution(first.id) == second
    assert finish(repository, second.id, second.attempt, True) is True


def test_unknown_id_wrong_attempt_and_nonrunning_states_are_rejected(
    engine: Engine,
) -> None:
    repository = ExecutionRepository(engine)
    reserved = create_reserved(repository)
    for succeed in (True, False):
        assert finish(repository, uuid4(), reserved.attempt, succeed) is False
        assert finish(repository, reserved.id, reserved.attempt + 1, succeed) is False
        assert repository.get_execution(reserved.id) == reserved

    for status in ("queued", "succeeded", "failed", "cancelled"):
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE executions.execution SET status = :status WHERE id = :id"),
                {"status": status, "id": reserved.id},
            )
        before = repository.get_execution(reserved.id)
        for succeed in (True, False):
            assert finish(repository, reserved.id, reserved.attempt, succeed) is False
            assert repository.get_execution(reserved.id) == before

    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE executions.execution SET status = 'running', lease_until = NULL WHERE id = :id"
            ),
            {"id": reserved.id},
        )
    for succeed in (True, False):
        assert finish(repository, reserved.id, reserved.attempt, succeed) is False


def test_competing_success_and_failure_allow_only_one_completion(
    engine: Engine,
) -> None:
    repository = ExecutionRepository(engine)
    reserved = create_reserved(repository)
    barrier = Barrier(2)

    def compete(succeed: bool) -> bool:
        barrier.wait(timeout=5)
        return finish(repository, reserved.id, reserved.attempt, succeed)

    with ThreadPoolExecutor(max_workers=2) as pool:
        success = pool.submit(compete, True)
        failure = pool.submit(compete, False)
        success_accepted = success.result(timeout=10)
        failure_accepted = failure.result(timeout=10)
    assert success_accepted != failure_accepted
    completed = repository.get_execution(reserved.id)
    assert completed is not None
    assert completed.status == ("succeeded" if success_accepted else "failed")
    assert completed.result == ({"value": 55} if success_accepted else None)


@pytest.mark.parametrize("succeed", [True, False])
def test_lease_is_rechecked_after_waiting_for_row_lock(
    engine: Engine, succeed: bool
) -> None:
    repository = ExecutionRepository(engine)
    reserved = create_reserved(repository)
    application_name = f"completion-{uuid4().hex}"
    contender = create_engine(
        engine.url,
        connect_args={
            "application_name": application_name,
            "options": "-cstatement_timeout=10000",
        },
    )
    try:
        # Release the held row lock before joining the worker thread.
        with ThreadPoolExecutor(max_workers=1) as pool:
            with engine.begin() as holder:
                holder.execute(
                    text(
                        "SELECT id FROM executions.execution WHERE id = :id FOR UPDATE"
                    ),
                    {"id": reserved.id},
                ).one()
                future = pool.submit(
                    finish,
                    ExecutionRepository(contender),
                    reserved.id,
                    reserved.attempt,
                    succeed,
                )
                deadline = monotonic() + 5
                with engine.connect() as observer:
                    while True:
                        waiting = observer.scalar(
                            text("""
                                SELECT EXISTS (
                                    SELECT 1 FROM pg_stat_activity
                                    WHERE application_name = :name
                                      AND wait_event_type = 'Lock'
                                )
                            """),
                            {"name": application_name},
                        )
                        observer.rollback()
                        if waiting:
                            break
                        assert monotonic() < deadline, (
                            "Completion did not wait for the row lock"
                        )
                        sleep(0.01)
                # This deadline is later than the blocked transaction's start time.
                holder.execute(
                    text(
                        "UPDATE executions.execution SET lease_until = clock_timestamp() WHERE id = :id"
                    ),
                    {"id": reserved.id},
                )
            assert future.result(timeout=10) is False
        current = repository.get_execution(reserved.id)
        assert current is not None
        assert current.status == "running"
        assert current.result is None
        assert current.error is None
        assert current.finished_at is None
    finally:
        contender.dispose()
