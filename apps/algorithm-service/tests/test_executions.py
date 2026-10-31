from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from algorithm_service.data_client import (
    DataClient,
    DataServiceUnavailable,
    InvalidDataServiceResponse,
    ScenarioNotFound,
)
from algorithm_service.executions import (
    ExecutionInputRejected,
    ExecutionNotFound,
    ExecutionService,
)
from algorithm_service.models import Execution
from algorithm_service.repository import ExecutionRepository
from algorithm_service.schemas import ScenarioVersion
from pydantic import JsonValue


@pytest.fixture
def scenario() -> ScenarioVersion:
    return ScenarioVersion(
        id=uuid4(),
        scenario_id=uuid4(),
        showcase_id="K01",
        version=1,
        name="Fibonacci",
        input={"n": 10},
    )


@pytest.fixture
def execution(scenario: ScenarioVersion) -> Execution:
    return Execution(
        id=uuid4(),
        algorithm_id="fibonacci.iterative",
        implementation_version="1",
        scenario_version_id=scenario.id,
        input_snapshot={"n": 10},
        status="queued",
        attempt=0,
        lease_until=None,
        result=None,
        error=None,
        duration_ms=None,
        created_at=datetime.now(UTC),
        started_at=None,
        finished_at=None,
    )


@pytest.mark.parametrize("n", [0, 10, 78])
def test_valid_scenario_creates_versioned_execution(
    scenario: ScenarioVersion, execution: Execution, n: int
) -> None:
    scenario.input = {"n": n}
    execution.input_snapshot = {"n": n}
    data_client = Mock(spec=DataClient)
    repository = Mock(spec=ExecutionRepository)
    data_client.get_scenario_version.return_value = scenario
    repository.create_execution.return_value = execution

    result = ExecutionService(data_client, repository).create_execution(scenario.id)

    assert result is execution
    data_client.get_scenario_version.assert_called_once_with(scenario.id)
    repository.create_execution.assert_called_once_with(
        algorithm_id="fibonacci.iterative",
        implementation_version="1",
        scenario_version_id=scenario.id,
        input_snapshot={"n": n},
    )


@pytest.mark.parametrize(
    "inputs",
    [
        {},
        {"n": -1},
        {"n": 79},
        {"n": "10"},
        {"n": True},
        {"n": 10.0},
        {"n": None},
        {"n": 10, "extra": 1},
    ],
)
def test_invalid_input_does_not_create_execution(
    scenario: ScenarioVersion, inputs: dict[str, JsonValue]
) -> None:
    scenario.input = inputs
    data_client = Mock(spec=DataClient)
    repository = Mock(spec=ExecutionRepository)
    data_client.get_scenario_version.return_value = scenario

    with pytest.raises(ExecutionInputRejected):
        ExecutionService(data_client, repository).create_execution(scenario.id)

    repository.create_execution.assert_not_called()


def test_unsupported_showcase_does_not_create_execution(
    scenario: ScenarioVersion,
) -> None:
    scenario.showcase_id = "K02"
    data_client = Mock(spec=DataClient)
    repository = Mock(spec=ExecutionRepository)
    data_client.get_scenario_version.return_value = scenario

    with pytest.raises(ExecutionInputRejected, match="Fibonacci showcase"):
        ExecutionService(data_client, repository).create_execution(scenario.id)

    repository.create_execution.assert_not_called()


@pytest.mark.parametrize(
    "error_type", [ScenarioNotFound, DataServiceUnavailable, InvalidDataServiceResponse]
)
def test_spring_failure_is_preserved_and_does_not_create_execution(
    error_type: type[Exception],
) -> None:
    data_client = Mock(spec=DataClient)
    repository = Mock(spec=ExecutionRepository)
    error = error_type("Cannot load scenario")
    data_client.get_scenario_version.side_effect = error

    with pytest.raises(error_type) as caught:
        ExecutionService(data_client, repository).create_execution(uuid4())

    assert caught.value is error
    repository.create_execution.assert_not_called()


def test_known_execution_is_read_without_calling_spring(execution: Execution) -> None:
    data_client = Mock(spec=DataClient)
    repository = Mock(spec=ExecutionRepository)
    repository.get_execution.return_value = execution

    result = ExecutionService(data_client, repository).get_execution(execution.id)

    assert result is execution
    repository.get_execution.assert_called_once_with(execution.id)
    data_client.get_scenario_version.assert_not_called()


def test_unknown_execution_is_reported() -> None:
    execution_id = uuid4()
    data_client = Mock(spec=DataClient)
    repository = Mock(spec=ExecutionRepository)
    repository.get_execution.return_value = None

    with pytest.raises(ExecutionNotFound, match=str(execution_id)):
        ExecutionService(data_client, repository).get_execution(execution_id)

    repository.get_execution.assert_called_once_with(execution_id)
    data_client.get_scenario_version.assert_not_called()
