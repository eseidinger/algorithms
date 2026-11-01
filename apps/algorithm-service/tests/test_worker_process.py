import os
import signal
import subprocess
import sys
from pathlib import Path
from time import monotonic, sleep
from uuid import uuid4

import pytest
from algorithm_service.config import Settings
from algorithm_service.models import Execution
from algorithm_service.repository import ExecutionRepository
from sqlalchemy.engine import Engine

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("stop_signal", [signal.SIGTERM, signal.SIGINT])
def test_worker_process_drains_persisted_jobs_and_stops_cleanly(
    database_settings: Settings,
    engine: Engine,
    tmp_path: Path,
    stop_signal: signal.Signals,
) -> None:
    repository = ExecutionRepository(engine)
    first = repository.create_execution(
        algorithm_id="fibonacci.iterative",
        implementation_version="1",
        scenario_version_id=uuid4(),
        input_snapshot={"n": 10},
    )
    assert repository.get_execution(first.id) == first
    assert first.status == "queued"

    environment = os.environ.copy()
    environment.update(
        {
            "PGHOST": database_settings.pghost,
            "PGPORT": str(database_settings.pgport),
            "PGDATABASE": database_settings.pgdatabase,
            "PGUSER": database_settings.pguser,
            "PGPASSWORD": database_settings.pgpassword.get_secret_value(),
            "PGSSLMODE": database_settings.pgsslmode,
            "WORKER_POLL_INTERVAL": "0.05",
            "WORKER_ERROR_RETRY_INTERVAL": "0.1",
            "WORKER_LEASE_SECONDS": "30",
        }
    )
    command = Path(sys.executable).with_name("algorithm-worker")
    assert command.exists(), "Install workspace packages with uv sync --all-packages"
    log_path = tmp_path / "worker.log"
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            [str(command)],
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:

            def wait_for_success(execution: Execution) -> Execution:
                deadline = monotonic() + 20
                while monotonic() < deadline:
                    assert process.poll() is None, log_path.read_text()
                    current = repository.get_execution(execution.id)
                    assert current is not None
                    if current.status == "succeeded":
                        return current
                    assert current.status != "failed", current.error
                    sleep(0.05)
                pytest.fail(f"Worker did not process job: {log_path.read_text()}")

            completed = wait_for_success(first)
            assert completed.result == {"value": 55}
            assert completed.attempt == 1
            # Work submitted after startup is processed by the same worker process.
            second = repository.create_execution(
                algorithm_id="fibonacci.iterative",
                implementation_version="1",
                scenario_version_id=uuid4(),
                input_snapshot={"n": 20},
            )
            assert wait_for_success(second).result == {"value": 6765}

            process.send_signal(stop_signal)
            assert process.wait(timeout=5) == 0
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    output = log_path.read_text()
    assert "Worker started" in output
    assert "Worker stopped" in output
