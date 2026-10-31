from collections.abc import AsyncIterator
from contextlib import ExitStack, asynccontextmanager

import httpx
from fastapi import FastAPI

from algorithm_service.api import router
from algorithm_service.config import Settings
from algorithm_service.data_client import DataClient
from algorithm_service.database import create_database_engine
from algorithm_service.executions import ExecutionService
from algorithm_service.repository import ExecutionRepository


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()

    with ExitStack() as stack:
        engine = create_database_engine(settings)
        stack.callback(engine.dispose)

        http_client = stack.enter_context(
            httpx.Client(
                base_url=settings.data_service_url,
                timeout=5.0,
                follow_redirects=False,
            )
        )

        app.state.execution_service = ExecutionService(
            data_client=DataClient(http_client),
            repository=ExecutionRepository(engine),
        )

        yield


app = FastAPI(title="Algorithm Lab API", lifespan=lifespan)
app.include_router(router)
