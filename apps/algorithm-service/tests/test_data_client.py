from uuid import UUID

import httpx
import pytest
from algorithm_service.data_client import (
    DataClient,
    DataServiceUnavailable,
    InvalidDataServiceResponse,
    ScenarioNotFound,
)

SCENARIO_ID = UUID("00000000-0000-4000-8000-000000000010")


@pytest.fixture
def scenario_payload() -> dict[str, object]:
    return {
        "id": str(SCENARIO_ID),
        "scenarioId": "00000000-0000-4000-8000-000000000001",
        "showcaseId": "K01",
        "version": 1,
        "name": "Fibonacci with n = 10",
        "input": {"n": 10},
    }


def test_loads_scenario_from_spring(scenario_payload: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.host == "data-service"
        assert request.url.path == f"/api/data/scenario-versions/{SCENARIO_ID}"
        return httpx.Response(200, json=scenario_payload)

    with httpx.Client(
        base_url="http://data-service",
        timeout=5.0,
        follow_redirects=False,
        transport=httpx.MockTransport(handler),
    ) as client:
        scenario = DataClient(client).get_scenario_version(SCENARIO_ID)

    assert scenario.id == SCENARIO_ID
    assert scenario.showcase_id == "K01"
    assert scenario.input == {"n": 10}


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (404, ScenarioNotFound),
        (500, DataServiceUnavailable),
        (503, DataServiceUnavailable),
        (403, InvalidDataServiceResponse),
        (302, InvalidDataServiceResponse),
        (204, InvalidDataServiceResponse),
    ],
)
def test_classifies_http_errors(
    status_code: int, expected_error: type[Exception]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    with (
        httpx.Client(
            base_url="http://data-service",
            transport=httpx.MockTransport(handler),
        ) as client,
        pytest.raises(expected_error),
    ):
        DataClient(client).get_scenario_version(SCENARIO_ID)


@pytest.mark.parametrize("error_type", [httpx.ReadTimeout, httpx.ConnectError])
def test_classifies_transport_errors_as_unavailable(
    error_type: type[httpx.RequestError],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error_type("Cannot complete request", request=request)

    with (
        httpx.Client(
            base_url="http://data-service",
            transport=httpx.MockTransport(handler),
        ) as client,
        pytest.raises(DataServiceUnavailable) as caught,
    ):
        DataClient(client).get_scenario_version(SCENARIO_ID)

    assert isinstance(caught.value.__cause__, error_type)


@pytest.mark.parametrize("body", [b"not JSON", b"{}", b"[]", b"null"])
def test_rejects_invalid_response_content(body: bytes) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    with (
        httpx.Client(
            base_url="http://data-service",
            transport=httpx.MockTransport(handler),
        ) as client,
        pytest.raises(InvalidDataServiceResponse) as caught,
    ):
        DataClient(client).get_scenario_version(SCENARIO_ID)

    assert isinstance(caught.value.__cause__, ValueError)


def test_rejects_a_different_scenario_id(scenario_payload: dict[str, object]) -> None:
    scenario_payload["id"] = "00000000-0000-4000-8000-000000000099"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=scenario_payload)

    with (
        httpx.Client(
            base_url="http://data-service",
            transport=httpx.MockTransport(handler),
        ) as client,
        pytest.raises(InvalidDataServiceResponse, match="does not match"),
    ):
        DataClient(client).get_scenario_version(SCENARIO_ID)
