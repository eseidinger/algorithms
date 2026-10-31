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
