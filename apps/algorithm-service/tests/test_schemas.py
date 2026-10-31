from uuid import UUID

import pytest
from algorithm_service.schemas import (
    CreateExecutionRequest,
    FibonacciInput,
    ScenarioVersion,
)
from pydantic import ValidationError

SCENARIO_VERSION_ID = "00000000-0000-4000-8000-000000000010"


def test_request_accepts_camel_case_scenario_id() -> None:
    request = CreateExecutionRequest.model_validate(
        {"scenarioVersionId": SCENARIO_VERSION_ID}
    )

    assert request.scenario_version_id == UUID(SCENARIO_VERSION_ID)
    assert request.model_dump(mode="json", by_alias=True) == {
        "scenarioVersionId": SCENARIO_VERSION_ID,
    }


def test_request_accepts_python_field_name() -> None:
    request = CreateExecutionRequest(scenario_version_id=UUID(SCENARIO_VERSION_ID))
    assert request.scenario_version_id == UUID(SCENARIO_VERSION_ID)


def test_request_rejects_input_override() -> None:
    with pytest.raises(ValidationError):
        CreateExecutionRequest.model_validate(
            {"scenarioVersionId": SCENARIO_VERSION_ID, "input": {"n": 20}},
        )


@pytest.mark.parametrize("payload", [{}, {"scenarioVersionId": "invalid"}])
def test_request_requires_valid_scenario_id(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        CreateExecutionRequest.model_validate(payload)


@pytest.mark.parametrize("n", [0, 10, 78])
def test_fibonacci_input_accepts_supported_values(n: int) -> None:
    assert FibonacciInput.model_validate({"n": n}).n == n


@pytest.mark.parametrize("n", [-1, 79, "10", True, False, 10.0, 10.5, None])
def test_fibonacci_input_rejects_invalid_values(n: object) -> None:
    with pytest.raises(ValidationError):
        FibonacciInput.model_validate({"n": n})


@pytest.mark.parametrize("payload", [{}, {"n": 10, "extra": 1}])
def test_fibonacci_input_rejects_missing_or_extra_fields(
    payload: dict[str, int],
) -> None:
    with pytest.raises(ValidationError):
        FibonacciInput.model_validate(payload)


def scenario_payload() -> dict[str, object]:
    return {
        "id": SCENARIO_VERSION_ID,
        "scenarioId": "00000000-0000-4000-8000-000000000001",
        "showcaseId": "K01",
        "version": 1,
        "name": "Fibonacci with n = 10",
        "input": {"n": 10},
    }


def test_scenario_accepts_spring_response_with_structured_input() -> None:
    payload = scenario_payload()
    scenario = ScenarioVersion.model_validate(payload)

    assert scenario.id == UUID(SCENARIO_VERSION_ID)
    assert scenario.input == {"n": 10}
    assert scenario.model_dump(mode="json", by_alias=True) == payload


@pytest.mark.parametrize(
    ("field", "value"),
    [("version", 0), ("version", -1), ("input", '{"n": 10}'), ("id", "invalid")],
)
def test_scenario_rejects_invalid_response_fields(field: str, value: object) -> None:
    payload = scenario_payload()
    payload[field] = value
    with pytest.raises(ValidationError):
        ScenarioVersion.model_validate(payload)
