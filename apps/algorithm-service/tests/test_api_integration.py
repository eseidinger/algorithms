from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

import httpx
import pytest
from algorithm_service.api import router
from algorithm_service.config import Settings
from algorithm_service.data_client import DataClient
from algorithm_service.database import create_database_engine
from algorithm_service.executions import ExecutionService
from algorithm_service.repository import ExecutionRepository
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.integration


@contextmanager
def running_api(
    settings: Settings, transport: httpx.MockTransport
) -> Iterator[TestClient]:
    engine = create_database_engine(settings)
    try:
        with httpx.Client(
            base_url="http://data-service", transport=transport
        ) as upstream:
            app = FastAPI()
            app.include_router(router)
            app.state.execution_service = ExecutionService(
                DataClient(upstream), ExecutionRepository(engine)
            )
            with TestClient(app) as client:
                yield client
    finally:
        engine.dispose()


def test_post_commits_job_and_new_api_instance_can_read_it(
    database_settings: Settings,
) -> None:
    scenario_id = uuid4()

    def spring(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/api/data/scenario-versions/{scenario_id}"
        return httpx.Response(
            200,
            json={
                "id": str(scenario_id),
                "scenarioId": str(uuid4()),
                "showcaseId": "K01",
                "version": 1,
                "name": "Fibonacci with n = 10",
                "input": {"n": 10},
            },
        )

    with running_api(database_settings, httpx.MockTransport(spring)) as client:
        response = client.post(
            "/api/algorithms/executions", json={"scenarioVersionId": str(scenario_id)}
        )
        assert response.status_code == 201
        location = response.headers["Location"]
        created = response.json()
        assert location == f"/api/algorithms/executions/{created['id']}"
        assert created["scenarioVersionId"] == str(scenario_id)
        assert created["algorithmId"] == "fibonacci.iterative"
        assert created["implementationVersion"] == "1"
        assert created["input"] == {"n": 10}
        assert created["status"] == "queued"
        assert created["result"] is None

    def unavailable_spring(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Reading an execution must not call Spring")

    with running_api(
        database_settings, httpx.MockTransport(unavailable_spring)
    ) as client:
        loaded = client.get(location)
        assert loaded.status_code == 200
        assert loaded.json() == created


def test_failed_scenario_resolution_and_validation_do_not_persist_jobs(
    database_settings: Settings,
) -> None:
    scenario_id = uuid4()
    base_payload = {
        "id": str(scenario_id),
        "scenarioId": str(uuid4()),
        "showcaseId": "K01",
        "version": 1,
        "name": "Fibonacci",
        "input": {"n": 10},
    }
    cases = [
        (httpx.Response(404), 404),
        (httpx.Response(503), 503),
        (httpx.Response(403), 502),
        (httpx.Response(200, content=b"not JSON"), 502),
        (httpx.Response(200, json={**base_payload, "showcaseId": "K02"}), 422),
        (httpx.Response(200, json={**base_payload, "input": {"n": 79}}), 422),
        (httpx.Response(200, json={**base_payload, "input": {"n": True}}), 422),
        (httpx.Response(200, json={**base_payload, "id": str(uuid4())}), 502),
    ]
    for upstream_response, expected_status in cases:

        def spring(
            request: httpx.Request, reply: httpx.Response = upstream_response
        ) -> httpx.Response:
            return reply

        with running_api(database_settings, httpx.MockTransport(spring)) as client:
            response = client.post(
                "/api/algorithms/executions",
                json={"scenarioVersionId": str(scenario_id)},
            )
            assert response.status_code == expected_status
            assert "Location" not in response.headers

    engine = create_database_engine(database_settings)
    try:
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT count(*) FROM executions.execution"))
                == 0
            )
    finally:
        engine.dispose()
