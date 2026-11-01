from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from algorithm_service.models import Execution
from algorithm_service.repository import ExecutionRepository
from algorithm_service.worker import process_next_execution
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture
def execution() -> Execution:
    return Execution(
        id=uuid4(),
        algorithm_id="fibonacci.iterative",
        implementation_version="1",
        scenario_version_id=uuid4(),
        input_snapshot={"n": 10},
        status="running",
        attempt=2,
        lease_until=datetime(2099, 1, 1, tzinfo=UTC),
        result=None,
        error=None,
        duration_ms=None,
        created_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        finished_at=None,
    )


@pytest.fixture
def repository(execution: Execution) -> Mock:
    repository = Mock(spec=ExecutionRepository)
    repository.reserve_execution.return_value = execution
    repository.complete_execution.return_value = True
    repository.fail_execution.return_value = True
    return repository


@pytest.fixture
def measured_time(monkeypatch: pytest.MonkeyPatch) -> None:
    times = iter([10.0, 10.002])
    monkeypatch.setattr("algorithm_service.worker.perf_counter", lambda: next(times))


def test_empty_queue_returns_idle_without_computation(
    repository: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository.reserve_execution.return_value = None
    calculate = Mock()
    monkeypatch.setattr("algorithm_service.worker.fibonacci", calculate)
    assert process_next_execution(repository, lease_seconds=60) == "idle"
    repository.reserve_execution.assert_called_once_with(lease_seconds=60)
    repository.complete_execution.assert_not_called()
    repository.fail_execution.assert_not_called()
    calculate.assert_not_called()


@pytest.mark.parametrize(("n", "value"), [(0, 0), (10, 55), (78, 8944394323791464)])
def test_valid_job_computes_result_for_reserved_attempt(
    repository: Mock, execution: Execution, measured_time: None, n: int, value: int
) -> None:
    execution.input_snapshot = {"n": n}
    assert process_next_execution(repository) == "succeeded"
    repository.complete_execution.assert_called_once_with(
        execution.id,
        attempt=2,
        result={"value": value},
        duration_ms=pytest.approx(2.0),
    )
    repository.fail_execution.assert_not_called()


@pytest.mark.parametrize(
    "updates",
    [
        {"algorithm_id": "unknown"},
        {"implementation_version": "2"},
        {"input_snapshot": {}},
        {"input_snapshot": {"n": -1}},
        {"input_snapshot": {"n": 79}},
        {"input_snapshot": {"n": "10"}},
        {"input_snapshot": {"n": True}},
        {"input_snapshot": {"n": 10, "extra": 1}},
    ],
)
def test_invalid_stored_job_fails_before_calculation(
    repository: Mock,
    execution: Execution,
    updates: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    measured_time: None,
) -> None:
    repository.reserve_execution.return_value = execution.model_copy(update=updates)
    calculate = Mock()
    monkeypatch.setattr("algorithm_service.worker.fibonacci", calculate)
    assert process_next_execution(repository) == "failed"
    calculate.assert_not_called()
    repository.complete_execution.assert_not_called()
    args = repository.fail_execution.call_args
    assert args.args == (execution.id,)
    assert args.kwargs["attempt"] == execution.attempt
    assert args.kwargs["duration_ms"] == pytest.approx(2.0)
    assert args.kwargs["error"]


def test_calculation_exception_is_recorded_as_failure(
    repository: Mock,
    execution: Execution,
    monkeypatch: pytest.MonkeyPatch,
    measured_time: None,
) -> None:
    monkeypatch.setattr(
        "algorithm_service.worker.fibonacci",
        Mock(side_effect=RuntimeError("Computation failed")),
    )
    assert process_next_execution(repository) == "failed"
    repository.fail_execution.assert_called_once_with(
        execution.id,
        attempt=execution.attempt,
        error="RuntimeError: Computation failed",
        duration_ms=pytest.approx(2.0),
    )
    repository.complete_execution.assert_not_called()


def test_rejected_success_is_discarded_without_failure_fallback(
    repository: Mock,
) -> None:
    repository.complete_execution.return_value = False
    assert process_next_execution(repository) == "discarded"
    repository.fail_execution.assert_not_called()


def test_rejected_failure_is_discarded(
    repository: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "algorithm_service.worker.fibonacci",
        Mock(side_effect=ValueError("bad computation")),
    )
    repository.fail_execution.return_value = False
    assert process_next_execution(repository) == "discarded"
    repository.complete_execution.assert_not_called()


@pytest.mark.parametrize(
    "operation", ["reserve_execution", "complete_execution", "fail_execution"]
)
def test_database_errors_propagate_without_another_completion_attempt(
    repository: Mock, operation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    error = SQLAlchemyError("Database unavailable")
    getattr(repository, operation).side_effect = error
    if operation == "fail_execution":
        monkeypatch.setattr(
            "algorithm_service.worker.fibonacci",
            Mock(side_effect=RuntimeError("Calculation failed")),
        )
    with pytest.raises(SQLAlchemyError) as caught:
        process_next_execution(repository)
    assert caught.value is error
    if operation == "reserve_execution":
        repository.complete_execution.assert_not_called()
        repository.fail_execution.assert_not_called()
    elif operation == "complete_execution":
        repository.complete_execution.assert_called_once()
        repository.fail_execution.assert_not_called()
    else:
        repository.complete_execution.assert_not_called()
        repository.fail_execution.assert_called_once()


def test_keyboard_interrupt_is_not_recorded_as_calculation_failure(
    repository: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "algorithm_service.worker.fibonacci", Mock(side_effect=KeyboardInterrupt())
    )
    with pytest.raises(KeyboardInterrupt):
        process_next_execution(repository)
    repository.fail_execution.assert_not_called()
    repository.complete_execution.assert_not_called()
