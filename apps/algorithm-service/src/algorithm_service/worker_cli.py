import logging
import signal
from contextlib import ExitStack
from threading import Event
from types import FrameType

from algorithm_service.config import Settings
from algorithm_service.database import create_database_engine
from algorithm_service.repository import ExecutionRepository
from algorithm_service.worker import run_worker


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings()
    stop_event = Event()

    def request_stop(_signum: int, _frame: FrameType | None) -> None:
        stop_event.set()

    with ExitStack() as stack:
        engine = create_database_engine(settings)
        stack.callback(engine.dispose)

        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handler = signal.signal(signum, request_stop)
            stack.callback(signal.signal, signum, previous_handler)

        logging.getLogger(__name__).info("Worker started")
        run_worker(
            ExecutionRepository(engine),
            stop_event,
            poll_interval=settings.worker_poll_interval,
            error_retry_interval=settings.worker_error_retry_interval,
            lease_seconds=settings.worker_lease_seconds,
        )
        logging.getLogger(__name__).info("Worker stopped")


if __name__ == "__main__":
    main()
