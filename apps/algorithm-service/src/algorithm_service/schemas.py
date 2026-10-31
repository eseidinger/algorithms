from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from pydantic.alias_generators import to_camel

from algorithm_service.models import Execution, ExecutionStatus


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        extra="forbid",
    )


class CreateExecutionRequest(ApiModel):
    scenario_version_id: UUID


class ScenarioVersion(ApiModel):
    id: UUID
    scenario_id: UUID
    showcase_id: str
    version: Annotated[int, Field(gt=0)]
    name: str
    input: dict[str, JsonValue]


class FibonacciInput(ApiModel):
    n: Annotated[int, Field(strict=True, ge=0, le=78)]


class ExecutionResponse(ApiModel):
    id: UUID
    scenario_version_id: UUID
    algorithm_id: str
    implementation_version: str
    status: ExecutionStatus
    input: dict[str, JsonValue]
    result: JsonValue
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: float | None

    @classmethod
    def from_execution(cls, execution: Execution) -> "ExecutionResponse":
        return cls(
            id=execution.id,
            scenario_version_id=execution.scenario_version_id,
            algorithm_id=execution.algorithm_id,
            implementation_version=execution.implementation_version,
            status=execution.status,
            input=execution.input_snapshot,
            result=execution.result,
            created_at=execution.created_at,
            started_at=execution.started_at,
            finished_at=execution.finished_at,
            duration_ms=execution.duration_ms,
        )
