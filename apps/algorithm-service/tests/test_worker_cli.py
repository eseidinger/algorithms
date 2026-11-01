import signal
from collections.abc import Callable
from threading import Event
from types import FrameType
from unittest.mock import Mock

import pytest
from algorithm_service import worker_cli
from algorithm_service.config import Settings
from algorithm_service.repository import ExecutionRepository
from pydantic import SecretStr


@pytest.mark.parametrize("raise_in_loop", [False, True])
def test_cli_restores_handlers_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch, raise_in_loop: bool
) -> None:
    settings = Settings(
        pgpassword=SecretStr("test"),
        worker_poll_interval=0.25,
        worker_error_retry_interval=2,
        worker_lease_seconds=60,
    )
    monkeypatch.setattr(worker_cli, "Settings", lambda: settings)
    engine = Mock()
    factory = Mock(return_value=engine)
    monkeypatch.setattr(worker_cli, "create_database_engine", factory)
    previous: dict[signal.Signals, Callable[[int, FrameType | None], None]] = {
        signal.SIGINT: Mock(),
        signal.SIGTERM: Mock(),
    }
    handlers = dict(previous)

    def register(
        signum: signal.Signals, handler: Callable[[int, FrameType | None], None]
    ) -> Callable[[int, FrameType | None], None]:
        old = handlers[signum]
        handlers[signum] = handler
        return old

    monkeypatch.setattr(worker_cli.signal, "signal", register)

    def run(repository: ExecutionRepository, stop: Event, **options: float) -> None:
        assert options == {
            "poll_interval": 0.25,
            "error_retry_interval": 2,
            "lease_seconds": 60,
        }
        assert not stop.is_set()
        engine.dispose.assert_not_called()
        for signum in (signal.SIGINT, signal.SIGTERM):
            handlers[signum](signum, None)
            assert stop.is_set()
            stop.clear()
        if raise_in_loop:
            raise RuntimeError("Unexpected failure")

    run_mock = Mock(side_effect=run)
    monkeypatch.setattr(worker_cli, "run_worker", run_mock)
    if raise_in_loop:
        with pytest.raises(RuntimeError, match="Unexpected failure"):
            worker_cli.main()
    else:
        worker_cli.main()
    factory.assert_called_once_with(settings)
    run_mock.assert_called_once()
    engine.dispose.assert_called_once_with()
    assert handlers == previous


def test_cli_cleans_up_after_partial_signal_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        worker_cli, "Settings", lambda: Settings(pgpassword=SecretStr("test"))
    )
    engine = Mock()
    monkeypatch.setattr(worker_cli, "create_database_engine", Mock(return_value=engine))
    previous = Mock()
    current_handler: object = previous

    def register(signum: signal.Signals, handler: object) -> object:
        nonlocal current_handler
        if signum == signal.SIGTERM:
            raise RuntimeError("Cannot register SIGTERM")
        old = current_handler
        current_handler = handler
        return old

    monkeypatch.setattr(worker_cli.signal, "signal", register)
    run = Mock()
    monkeypatch.setattr(worker_cli, "run_worker", run)
    with pytest.raises(RuntimeError, match="Cannot register SIGTERM"):
        worker_cli.main()
    run.assert_not_called()
    engine.dispose.assert_called_once_with()
    assert current_handler is previous
