from uuid import UUID

from pydantic import ValidationError

from algorithm_service.data_client import DataClient
from algorithm_service.models import Execution
from algorithm_service.repository import ExecutionRepository
from algorithm_service.schemas import FibonacciInput

ALGORITHM_ID = "fibonacci.iterative"
IMPLEMENTATION_VERSION = "1"


class ExecutionInputRejected(Exception):
    pass


class ExecutionNotFound(Exception):
    pass


class ExecutionService:
    def __init__(
        self,
        data_client: DataClient,
        repository: ExecutionRepository,
    ) -> None:
        self._data_client = data_client
        self._repository = repository

    def create_execution(self, scenario_version_id: UUID) -> Execution:
        scenario = self._data_client.get_scenario_version(scenario_version_id)

        if scenario.showcase_id != "K01":
            raise ExecutionInputRejected(
                "Only the Fibonacci showcase is currently supported"
            )

        try:
            inputs = FibonacciInput.model_validate(scenario.input)
        except ValidationError as exc:
            raise ExecutionInputRejected(
                "Fibonacci requires an integer n between 0 and 78"
            ) from exc

        return self._repository.create_execution(
            algorithm_id=ALGORITHM_ID,
            implementation_version=IMPLEMENTATION_VERSION,
            scenario_version_id=scenario.id,
            input_snapshot={"n": inputs.n},
        )

    def get_execution(self, execution_id: UUID) -> Execution:
        execution = self._repository.get_execution(execution_id)

        if execution is None:
            raise ExecutionNotFound(f"Execution {execution_id} does not exist")

        return execution
