from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, JsonValue

ExecutionStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancelled",
]


class Execution(BaseModel):
    id: UUID
    algorithm_id: str
    implementation_version: str
    scenario_version_id: UUID
    input_snapshot: dict[str, JsonValue]
    status: ExecutionStatus
    attempt: int
    lease_until: datetime | None
    result: JsonValue
    error: str | None
    duration_ms: float | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
