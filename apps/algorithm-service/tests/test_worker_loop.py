from threading import Event, Thread
from unittest.mock import Mock, call

import pytest
from algorithm_service.repository import ExecutionRepository
from algorithm_service.worker import run_worker
from sqlalchemy.exc import SQLAlchemyError


def test_already_stopped_worker_does_not_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = Mock()
    monkeypatch.setattr("algorithm_service.worker.process_next_execution", process)
    stop = Event()
    stop.set()
    run_worker(
        Mock(spec=ExecutionRepository),
        stop,
        poll_interval=1,
        error_retry_interval=5,
        lease_seconds=30,
    )
    process.assert_not_called()


def test_worker_drains_jobs_then_waits_only_when_idle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stop = Event()
    wait = Mock(side_effect=lambda interval: stop.set())
    monkeypatch.setattr(stop, "wait", wait)
    process = Mock(side_effect=["succeeded", "failed", "discarded", "idle"])
    monkeypatch.setattr("algorithm_service.worker.process_next_execution", process)
    repository = Mock(spec=ExecutionRepository)

    run_worker(
        repository, stop, poll_interval=2, error_retry_interval=5, lease_seconds=60
    )

    assert process.call_args_list == [call(repository, lease_seconds=60)] * 4
    wait.assert_called_once_with(2)


def test_database_error_waits_then_processing_recovers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stop = Event()
    logger = Mock()
    monkeypatch.setattr("algorithm_service.worker.logger", logger)

    def wait_for(interval: float) -> None:
        if interval == 1:
            stop.set()

    wait = Mock(side_effect=wait_for)
    monkeypatch.setattr(stop, "wait", wait)
    process = Mock(
        side_effect=[SQLAlchemyError("Database unavailable"), "succeeded", "idle"]
    )
    monkeypatch.setattr("algorithm_service.worker.process_next_execution", process)

    run_worker(
        Mock(spec=ExecutionRepository),
        stop,
        poll_interval=1,
        error_retry_interval=5,
        lease_seconds=30,
    )

    assert wait.call_args_list == [call(5), call(1)]
    assert process.call_count == 3
    logger.exception.assert_called_once_with("Worker database operation failed")


def test_stop_during_job_allows_current_iteration_to_finish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stop = Event()

    def finish_job(repository: ExecutionRepository, *, lease_seconds: int) -> str:
        stop.set()
        return "succeeded"

    process = Mock(side_effect=finish_job)
    monkeypatch.setattr("algorithm_service.worker.process_next_execution", process)
    wait = Mock()
    monkeypatch.setattr(stop, "wait", wait)
    run_worker(
        Mock(spec=ExecutionRepository),
        stop,
        poll_interval=1,
        error_retry_interval=5,
        lease_seconds=30,
    )
    process.assert_called_once()
    wait.assert_not_called()


@pytest.mark.parametrize("database_failure", [False, True])
def test_stop_interrupts_polling_and_error_wait(
    monkeypatch: pytest.MonkeyPatch, database_failure: bool
) -> None:
    stop = Event()
    entered_wait = Event()
    real_wait = stop.wait

    def observe_wait(timeout: float) -> bool:
        entered_wait.set()
        return real_wait(timeout)

    monkeypatch.setattr(stop, "wait", observe_wait)
    process = Mock(return_value="idle")
    if database_failure:
        process.side_effect = SQLAlchemyError("Database unavailable")
    monkeypatch.setattr("algorithm_service.worker.process_next_execution", process)
    errors: list[BaseException] = []

    def run() -> None:
        try:
            run_worker(
                Mock(spec=ExecutionRepository),
                stop,
                poll_interval=60,
                error_retry_interval=60,
                lease_seconds=30,
            )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    thread = Thread(target=run, daemon=True)
    thread.start()
    try:
        assert entered_wait.wait(timeout=2)
        stop.set()
        thread.join(timeout=2)
        assert not thread.is_alive()
        assert not errors
        process.assert_called_once()
    finally:
        stop.set()
        thread.join(timeout=2)


def test_unexpected_error_propagates_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("Programming error")
    process = Mock(side_effect=error)
    monkeypatch.setattr("algorithm_service.worker.process_next_execution", process)
    stop = Event()
    wait = Mock()
    monkeypatch.setattr(stop, "wait", wait)
    with pytest.raises(RuntimeError) as caught:
        run_worker(
            Mock(spec=ExecutionRepository),
            stop,
            poll_interval=1,
            error_retry_interval=5,
            lease_seconds=30,
        )
    assert caught.value is error
    wait.assert_not_called()
