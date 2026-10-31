import asyncio
from unittest.mock import Mock, patch

import httpx
import pytest
from algorithm_service.config import Settings
from algorithm_service.executions import ExecutionService
from algorithm_service.main import lifespan
from fastapi import FastAPI


def test_lifespan_registers_service_and_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PGPASSWORD", "test")
    engine = Mock()
    http_client = httpx.Client()
    app = FastAPI()

    async def run() -> None:
        async with lifespan(app):
            assert isinstance(app.state.execution_service, ExecutionService)
            assert not http_client.is_closed
            engine.dispose.assert_not_called()

    with (
        patch(
            "algorithm_service.main.create_database_engine", return_value=engine
        ) as factory,
        patch(
            "algorithm_service.main.httpx.Client", return_value=http_client
        ) as client_factory,
    ):
        asyncio.run(run())

    assert isinstance(factory.call_args.args[0], Settings)
    client_factory.assert_called_once_with(
        base_url=Settings().data_service_url,
        timeout=5.0,
        follow_redirects=False,
    )
    assert http_client.is_closed
    engine.dispose.assert_called_once_with()


def test_lifespan_disposes_engine_when_client_initialization_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PGPASSWORD", "test")
    engine = Mock()

    async def run() -> None:
        async with lifespan(FastAPI()):
            pytest.fail("Startup should not succeed")

    with (
        patch("algorithm_service.main.create_database_engine", return_value=engine),
        patch(
            "algorithm_service.main.httpx.Client",
            side_effect=RuntimeError("initialization failed"),
        ),
        pytest.raises(RuntimeError, match="initialization failed"),
    ):
        asyncio.run(run())

    engine.dispose.assert_called_once_with()
