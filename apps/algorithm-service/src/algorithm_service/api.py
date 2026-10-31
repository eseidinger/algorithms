from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response

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
from algorithm_service.schemas import CreateExecutionRequest, ExecutionResponse

router = APIRouter(prefix="/api/algorithms")


def get_execution_service(request: Request) -> ExecutionService:
    return cast(ExecutionService, request.app.state.execution_service)


ExecutionServiceDependency = Annotated[
    ExecutionService,
    Depends(get_execution_service),
]


@router.post("/executions", response_model=ExecutionResponse, status_code=201)
def create_execution(
    body: CreateExecutionRequest,
    response: Response,
    service: ExecutionServiceDependency,
) -> ExecutionResponse:
    try:
        execution = service.create_execution(body.scenario_version_id)
    except ScenarioNotFound as exc:
        raise HTTPException(
            status_code=404, detail="Scenario version not found"
        ) from exc
    except ExecutionInputRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DataServiceUnavailable as exc:
        raise HTTPException(status_code=503, detail="Data service unavailable") from exc
    except InvalidDataServiceResponse as exc:
        raise HTTPException(
            status_code=502, detail="Invalid response from data service"
        ) from exc

    response.headers["Location"] = f"/api/algorithms/executions/{execution.id}"
    return ExecutionResponse.from_execution(execution)


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
def get_execution(
    execution_id: UUID,
    service: ExecutionServiceDependency,
) -> ExecutionResponse:
    try:
        execution = service.get_execution(execution_id)
    except ExecutionNotFound as exc:
        raise HTTPException(status_code=404, detail="Execution not found") from exc

    return ExecutionResponse.from_execution(execution)
