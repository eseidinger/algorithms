from time import perf_counter
from typing import Literal

from algorithm_lab.fibonacci import fibonacci

from algorithm_service.executions import ALGORITHM_ID, IMPLEMENTATION_VERSION
from algorithm_service.repository import ExecutionRepository
from algorithm_service.schemas import FibonacciInput

WorkerOutcome = Literal["idle", "succeeded", "failed", "discarded"]


def process_next_execution(
    repository: ExecutionRepository,
    *,
    lease_seconds: int = 30,
) -> WorkerOutcome:
    execution = repository.reserve_execution(lease_seconds=lease_seconds)
    if execution is None:
        return "idle"

    started = perf_counter()
    try:
        if execution.algorithm_id != ALGORITHM_ID:
            raise ValueError("Unsupported algorithm")
        if execution.implementation_version != IMPLEMENTATION_VERSION:
            raise ValueError("Unsupported implementation version")

        inputs = FibonacciInput.model_validate(execution.input_snapshot)
        value = fibonacci(inputs.n)
    # This boundary converts computation failures only; persistence errors propagate.
    except Exception as exc:  # noqa: BLE001
        duration_ms = (perf_counter() - started) * 1000
        accepted = repository.fail_execution(
            execution.id,
            attempt=execution.attempt,
            error=f"{type(exc).__name__}: {exc}",
            duration_ms=duration_ms,
        )
        return "failed" if accepted else "discarded"

    duration_ms = (perf_counter() - started) * 1000
    accepted = repository.complete_execution(
        execution.id,
        attempt=execution.attempt,
        result={"value": value},
        duration_ms=duration_ms,
    )
    return "succeeded" if accepted else "discarded"
