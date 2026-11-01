from uuid import UUID, uuid4

from pydantic import JsonValue
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

from algorithm_service.models import Execution


class ExecutionRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_execution(
        self,
        *,
        algorithm_id: str,
        implementation_version: str,
        scenario_version_id: UUID,
        input_snapshot: dict[str, JsonValue],
    ) -> Execution:
        statement = text(
            """
            INSERT INTO executions.execution (
                id,
                algorithm_id,
                implementation_version,
                scenario_version_id,
                input_snapshot
            )
            VALUES (
                :id,
                :algorithm_id,
                :implementation_version,
                :scenario_version_id,
                :input_snapshot
            )
            RETURNING *
            """
        ).bindparams(bindparam("input_snapshot", type_=JSONB))

        parameters = {
            "id": uuid4(),
            "algorithm_id": algorithm_id,
            "implementation_version": implementation_version,
            "scenario_version_id": scenario_version_id,
            "input_snapshot": input_snapshot,
        }

        with self._engine.begin() as connection:
            row = connection.execute(statement, parameters).mappings().one()
            execution = Execution.model_validate(dict(row))

        return execution

    def get_execution(self, execution_id: UUID) -> Execution | None:
        statement = text(
            """
            SELECT *
            FROM executions.execution
            WHERE id = :id
            """
        )

        with self._engine.connect() as connection:
            row = (
                connection.execute(statement, {"id": execution_id})
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None

            return Execution.model_validate(dict(row))

    def reserve_execution(self, *, lease_seconds: int = 30) -> Execution | None:
        if lease_seconds <= 0:
            raise ValueError("Lease duration must be positive")

        statement = text(
            """
            WITH candidate AS (
                SELECT id
                FROM executions.execution
                WHERE status = 'queued'
                   OR (
                       status = 'running'
                       AND lease_until <= CURRENT_TIMESTAMP
                   )
                ORDER BY created_at, id
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            UPDATE executions.execution AS execution
            SET status = 'running',
                attempt = execution.attempt + 1,
                lease_until = CURRENT_TIMESTAMP
                    + (:lease_seconds * INTERVAL '1 second'),
                started_at = CURRENT_TIMESTAMP,
                finished_at = NULL,
                result = NULL,
                error = NULL,
                duration_ms = NULL
            FROM candidate
            WHERE execution.id = candidate.id
            RETURNING execution.*
            """
        )

        with self._engine.begin() as connection:
            row = (
                connection.execute(statement, {"lease_seconds": lease_seconds})
                .mappings()
                .one_or_none()
            )
            execution = Execution.model_validate(dict(row)) if row is not None else None

        return execution

    def complete_execution(
        self,
        execution_id: UUID,
        *,
        attempt: int,
        result: dict[str, JsonValue],
        duration_ms: float,
    ) -> bool:
        statement = text(
            """
            UPDATE executions.execution
            SET status = 'succeeded',
                result = :result,
                error = NULL,
                duration_ms = :duration_ms,
                finished_at = clock_timestamp(),
                lease_until = NULL
            WHERE id = :id
              AND attempt = :attempt
              AND status = 'running'
              AND lease_until > clock_timestamp()
            RETURNING id
            """
        ).bindparams(bindparam("result", type_=JSONB))

        with self._engine.begin() as connection:
            # Acquire the lock before checking time, including after a lock wait.
            connection.execute(
                text("SELECT id FROM executions.execution WHERE id = :id FOR UPDATE"),
                {"id": execution_id},
            ).all()
            updated_id = connection.execute(
                statement,
                {
                    "id": execution_id,
                    "attempt": attempt,
                    "result": result,
                    "duration_ms": duration_ms,
                },
            ).scalar_one_or_none()

        return updated_id is not None

    def fail_execution(
        self,
        execution_id: UUID,
        *,
        attempt: int,
        error: str,
        duration_ms: float,
    ) -> bool:
        statement = text(
            """
            UPDATE executions.execution
            SET status = 'failed',
                result = NULL,
                error = :error,
                duration_ms = :duration_ms,
                finished_at = clock_timestamp(),
                lease_until = NULL
            WHERE id = :id
              AND attempt = :attempt
              AND status = 'running'
              AND lease_until > clock_timestamp()
            RETURNING id
            """
        )

        with self._engine.begin() as connection:
            connection.execute(
                text("SELECT id FROM executions.execution WHERE id = :id FOR UPDATE"),
                {"id": execution_id},
            ).all()
            updated_id = connection.execute(
                statement,
                {
                    "id": execution_id,
                    "attempt": attempt,
                    "error": error,
                    "duration_ms": duration_ms,
                },
            ).scalar_one_or_none()

        return updated_id is not None
