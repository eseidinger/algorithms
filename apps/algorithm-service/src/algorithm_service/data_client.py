from uuid import UUID

import httpx

from algorithm_service.schemas import ScenarioVersion


class ScenarioNotFound(Exception):
    pass


class DataServiceUnavailable(Exception):
    pass


class InvalidDataServiceResponse(Exception):
    pass


class DataClient:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def get_scenario_version(self, scenario_version_id: UUID) -> ScenarioVersion:
        try:
            response = self._client.get(
                f"/api/data/scenario-versions/{scenario_version_id}"
            )
        except httpx.RequestError as exc:
            raise DataServiceUnavailable("Could not reach the data service") from exc

        if response.status_code == 404:
            raise ScenarioNotFound(
                f"Scenario version {scenario_version_id} does not exist"
            )

        if response.status_code >= 500:
            raise DataServiceUnavailable("The data service reported an error")

        if response.status_code != 200:
            raise InvalidDataServiceResponse(
                f"Unexpected HTTP status {response.status_code}"
            )

        try:
            scenario = ScenarioVersion.model_validate(response.json())
        except ValueError as exc:
            raise InvalidDataServiceResponse(
                "The data service returned invalid scenario data"
            ) from exc

        if scenario.id != scenario_version_id:
            raise InvalidDataServiceResponse(
                "The returned scenario version does not match the request"
            )

        return scenario
