from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from algorithm_service.api import get_execution_service, router
from algorithm_service.data_client import (
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
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def execution() -> Execution:
    return Execution(
        id=uuid4(),
        algorithm_id="fibonacci.iterative",
        implementation_version="1",
        scenario_version_id=uuid4(),
        input_snapshot={"n": 10},
        status="queued",
        attempt=0,
        lease_until=None,
        result=None,
        error=None,
        duration_ms=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        started_at=None,
        finished_at=None,
    )


@pytest.fixture
def service() -> Mock:
    return Mock(spec=ExecutionService)


@pytest.fixture
def client(service: Mock) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_execution_service] = lambda: service
    with TestClient(app) as client:
        yield client


def test_get_returns_public_camel_case_response(
    client: TestClient, service: Mock, execution: Execution
) -> None:
    service.get_execution.return_value = execution

    response = client.get(f"/api/algorithms/executions/{execution.id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(execution.id),
        "scenarioVersionId": str(execution.scenario_version_id),
        "algorithmId": "fibonacci.iterative",
        "implementationVersion": "1",
        "status": "queued",
        "input": {"n": 10},
        "result": None,
        "createdAt": "2026-01-01T00:00:00Z",
        "startedAt": None,
        "finishedAt": None,
        "durationMs": None,
    }
    service.get_execution.assert_called_once_with(execution.id)


def test_get_returns_completed_result(
    client: TestClient, service: Mock, execution: Execution
) -> None:
    execution.status = "succeeded"
    execution.result = {"value": 55}
    execution.started_at = execution.created_at
    execution.finished_at = execution.created_at
    execution.duration_ms = 0.5
    service.get_execution.return_value = execution

    response = client.get(f"/api/algorithms/executions/{execution.id}")

    assert response.status_code == 200
    assert response.json()["result"] == {"value": 55}
    assert response.json()["status"] == "succeeded"
    assert response.json()["durationMs"] == 0.5


def test_get_unknown_execution_returns_safe_not_found(
    client: TestClient, service: Mock
) -> None:
    service.get_execution.side_effect = ExecutionNotFound("internal details")

    response = client.get(f"/api/algorithms/executions/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Execution not found"}


def test_get_invalid_uuid_rejected_before_repository_access(
    client: TestClient, service: Mock
) -> None:
    response = client.get("/api/algorithms/executions/invalid")

    assert response.status_code == 422
    service.get_execution.assert_not_called()


def test_openapi_exposes_execution_route(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert (
        "get" in response.json()["paths"]["/api/algorithms/executions/{execution_id}"]
    )
    assert "post" in response.json()["paths"]["/api/algorithms/executions"]


def test_post_creates_execution_and_returns_location(
    client: TestClient, service: Mock, execution: Execution
) -> None:
    service.create_execution.return_value = execution
    response = client.post(
        "/api/algorithms/executions",
        json={"scenarioVersionId": str(execution.scenario_version_id)},
    )

    assert response.status_code == 201
    assert response.headers["Location"] == f"/api/algorithms/executions/{execution.id}"
    assert response.json()["id"] == str(execution.id)
    assert response.json()["scenarioVersionId"] == str(execution.scenario_version_id)
    assert response.json()["status"] == "queued"
    assert response.json()["input"] == {"n": 10}
    assert response.json()["result"] is None
    service.create_execution.assert_called_once_with(execution.scenario_version_id)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"scenarioVersionId": "invalid"},
        {"scenarioVersionId": None},
        {
            "scenarioVersionId": "00000000-0000-4000-8000-000000000010",
            "input": {"n": 20},
        },
    ],
)
def test_post_rejects_invalid_request(
    client: TestClient, service: Mock, payload: dict[str, object]
) -> None:
    response = client.post("/api/algorithms/executions", json=payload)
    assert response.status_code == 422
    assert "Location" not in response.headers
    service.create_execution.assert_not_called()


@pytest.mark.parametrize(
    ("error", "expected_status", "detail"),
    [
        (ScenarioNotFound("internal details"), 404, "Scenario version not found"),
        (ExecutionInputRejected("Unsupported scenario"), 422, "Unsupported scenario"),
        (DataServiceUnavailable("internal details"), 503, "Data service unavailable"),
        (
            InvalidDataServiceResponse("internal details"),
            502,
            "Invalid response from data service",
        ),
    ],
)
def test_post_translates_service_failures(
    client: TestClient,
    service: Mock,
    error: Exception,
    expected_status: int,
    detail: str,
) -> None:
    service.create_execution.side_effect = error
    response = client.post(
        "/api/algorithms/executions", json={"scenarioVersionId": str(uuid4())}
    )
    assert response.status_code == expected_status
    assert response.json() == {"detail": detail}
    assert "Location" not in response.headers


def test_post_does_not_expose_unexpected_errors(
    client: TestClient, service: Mock
) -> None:
    service.create_execution.side_effect = RuntimeError("private database details")
    with TestClient(client.app, raise_server_exceptions=False) as error_client:
        response = error_client.post(
            "/api/algorithms/executions", json={"scenarioVersionId": str(uuid4())}
        )
    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    assert "Location" not in response.headers
