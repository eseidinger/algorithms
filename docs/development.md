# Local Development, Builds, and Database Migrations

See the [architecture overview](architecture.md) for component responsibilities, contracts, and scenario sequence diagrams.

## Current Scope

The repository contains a React/TypeScript frontend, a Kotlin/Spring Boot data service, a Python service package, and an independent Python algorithm package. PostgreSQL runs in Docker; applications run directly on the host during development.

The frontend loads the showcase catalog from Spring and links to the Fibonacci scenario page. That page displays the immutable input and starts an execution through FastAPI, navigating to its persistent detail URL after creation. Loading and error states are handled. Spring initializes the showcase catalog and immutable scenario versions and exposes read-only catalog APIs and Actuator health endpoints. Python has database configuration, Alembic migrations, a Spring HTTP client, an execution repository and service, and a FastAPI application for creating and reading executions. Its generated CLI still prints a greeting; start the API through Uvicorn as shown below. A separately started worker processes durable jobs continuously. The browser can follow a Fibonacci job through polling to its result.

## Prerequisites

- Git
- Docker Engine with Docker Compose v2, including support for `up --wait`
- Node.js 24 and npm for the frontend
- uv for Python dependencies, environments, and builds
- JDK 25 for Spring Boot

Python 3.13 is selected by `.python-version` and the workspace's Python constraint. uv can install it. Gradle 9.8.2 is supplied through the committed wrapper; no global Gradle installation is needed.

Commands below assume Bash and the repository root unless another working directory is shown. Initial dependency installation requires network access.

## Repository Layout

```text
algorithm-lab/
├── apps/
│   ├── web/                     # React, Vite, TypeScript, ESLint
│   ├── algorithm-service/       # Python service and Alembic migrations
│   └── data-service/            # Spring Boot and Flyway migrations
├── packages/
│   └── algorithms/              # Independent Python algorithm package
├── infra/
│   ├── compose.yaml             # Local PostgreSQL
│   └── postgres/001-init.sql     # Database roles and schemas
├── pyproject.toml               # Python workspace and development tools
├── uv.lock
└── docs/
```

## Install Dependencies

From the repository root:

```bash
uv python install 3.13
uv sync --all-packages --frozen
npm --prefix apps/web ci
```

The Python workspace uses one `.venv` and one `uv.lock`. The service consumes `algorithm-lab` as an editable workspace dependency. Use `uv run` to select the project environment; activating Conda or manually activating `.venv` is unnecessary.

`--frozen` and `npm ci` install the committed dependency versions. For intentional dependency updates, use `uv add` or `npm install` and commit the corresponding manifest and lockfile changes.

The frontend currently uses TypeScript 5.9 because `openapi-typescript` 7 requires TypeScript 5. The form integration uses `@hookform/resolvers` 5. Preserve these compatible major versions when adding dependencies; do not bypass peer dependency conflicts with `--force` or `--legacy-peer-deps`.

## Start PostgreSQL

```bash
docker compose -f infra/compose.yaml up -d --wait
docker compose -f infra/compose.yaml ps
```

The service is exposed only on `127.0.0.1:5432`. Its named volume persists data between container restarts. The PostgreSQL 18 volume is mounted at `/var/lib/postgresql`.

The initial database is `algorithm_lab`:

| Consumer | Schema | Role | Local password |
| --- | --- | --- | --- |
| Spring / Flyway | `catalog` | `catalog_app` | `catalog_local` |
| Python / Alembic | `executions` | `execution_app` | `execution_local` |
| Local administration | All schemas | `postgres` | `postgres_local` |

These credentials belong only to local development. Applications use their respective non-administrator roles. The initialization script creates the roles and schemas and configures each application's default search path.

Scripts in `/docker-entrypoint-initdb.d` run only when the database volume is empty. Editing `001-init.sql` does not change an existing database.

If host port 5432 is occupied, change the Compose mapping to `127.0.0.1:5433:5432` and set `PGPORT=5433` for host applications. Commands executed inside the container still use port 5432.

## Application Configuration

| Variable | Spring default | Python default |
| --- | --- | --- |
| `PGHOST` | `localhost` | `localhost` |
| `PGPORT` | `5432` | `5432` |
| `PGDATABASE` | `algorithm_lab` | `algorithm_lab` |
| `PGUSER` | `catalog_app` | `execution_app` |
| `PGPASSWORD` | Required | Required |
| `PGSSLMODE` | Not currently mapped in the JDBC URL | `prefer` |
| `PORT` | `8080` | Not read by the Python application; pass Uvicorn `--port` (locally `8000`) |
| `DATA_SERVICE_URL` | Not used | `http://localhost:8080` |
| `WORKER_POLL_INTERVAL` | Not used | `1.0` seconds; wait when no work is available |
| `WORKER_ERROR_RETRY_INTERVAL` | Not used | `5.0` seconds; wait after a SQLAlchemy error |
| `WORKER_LEASE_SECONDS` | Not used | `30` seconds |

Spring sets `currentSchema=catalog` in its JDBC URL. Python uses the synchronous `postgresql+psycopg` SQLAlchemy driver and explicitly sets `search_path=executions` when connecting.

Pass environment variables to each command as shown below. This avoids accidentally sharing Spring credentials with Python in the same terminal. Neither application is currently configured to load a `.env` file automatically. Do not commit actual deployment credentials.

## Initialize Migrations and Run Applications

### Python migrations

Apply the existing migrations before using the execution tables:

```bash
cd apps/algorithm-service
PGPASSWORD=execution_local uv run alembic upgrade head
PGPASSWORD=execution_local uv run alembic current
cd ../..
```

The current initial revision is `e6dbe344f903`. It creates `executions.execution` with these statuses: `queued`, `running`, `succeeded`, `failed`, and `cancelled`. Alembic records its state in `executions.alembic_version`.

### Spring data service

Start Spring in a dedicated terminal:

```bash
cd apps/data-service
PGPASSWORD=catalog_local ./gradlew bootRun
```

Flyway runs automatically during application startup. It creates `catalog.showcase` and inserts the `K01` Fibonacci entry. Migration state is stored in `catalog.flyway_schema_history`.

From another terminal:

```bash
curl -f http://localhost:8080/actuator/health
curl -f http://localhost:8080/actuator/health/readiness
```

Both should report `UP`.

Read the catalog and the seeded Fibonacci scenario version:

```bash
curl -f http://localhost:8080/api/data/showcases
curl -f http://localhost:8080/api/data/scenario-versions/00000000-0000-4000-8000-000000000010
```

The scenario response contains `id`, `scenarioId`, `showcaseId`, `version`, `name`, and a structured `input` object (`{"n": 10}`). A well-formed unknown UUID returns HTTP 404; a malformed UUID returns HTTP 400. The routes provide read access only.

Stop the application with Ctrl+C.

### Web frontend

In another terminal, starting from the repository root:

```bash
cd apps/web
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`. The root page loads `/api/data/showcases` through TanStack Query and displays the returned names and descriptions as cards. Zod validates the JSON response. Loading, empty-catalog, and request/response-error states are handled; failed requests are retried once. This step requires PostgreSQL and Spring, but not FastAPI or the worker.

The Vite development proxy forwards `/api/data` to `http://127.0.0.1:8080` and `/api/algorithms` to `http://127.0.0.1:8000`, preserving the complete path. Browser calls use relative URLs and the frontend origin, so a separate cross-origin setup is unnecessary for these proxied requests. Restart Vite after changing proxy configuration. If Vite selects another available port, use the printed port in the browser and any checks.

```bash
curl -i http://localhost:5173/api/data/showcases
```

A running Spring service should return the same catalog through this URL as through port 8080. Open the K01 card to navigate to `/showcases/K01`, which also supports direct entry. This page loads the seeded scenario version and displays its read-only input (`n = 10`). With FastAPI running, click **Run Fibonacci** to POST only the scenario-version reference and navigate to `/executions/{id}`. The button is disabled while the request is pending; POST is never retried automatically. A failed confirmation can still mean the server created a job. Each new click can create another job. The worker is needed to calculate the result, but not to create the job. The execution page also supports direct entry and reloads. It polls GET every second while `queued` or `running`, stops on a terminal state, and displays the result and duration. Invalid IDs make no request; HTTP 404 has a distinct message. A request failure stops interval polling; **Retry** repeats only GET, never POST. Production deployment still needs the planned web server/reverse proxy.

### Python execution API

After applying Alembic, start the API in a separate terminal from the repository root:

```bash
PGPASSWORD=execution_local \
DATA_SERVICE_URL=http://localhost:8080 \
uv run --package algorithm-service \
uvicorn algorithm_service.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for Swagger UI or `/openapi.json` for the API schema. The application creates an engine and one HTTPX client at startup and closes both at shutdown, including cleanup after partial initialization failure. Startup does not run migrations or verify database connectivity; the first database operation opens a connection.

```bash
curl -i http://localhost:8000/api/algorithms/executions/00000000-0000-4000-8000-000000000099
```

An unknown execution UUID returns HTTP 404 with `{"detail":"Execution not found"}`. A malformed UUID returns HTTP 422. Existing jobs return a camelCase response containing `input`, result and timestamps; internal lease, attempt, and error fields are omitted. GET does not contact Spring. Create an execution while Spring is running on `DATA_SERVICE_URL`:

```bash
curl -i -X POST http://localhost:8000/api/algorithms/executions \
  -H 'Content-Type: application/json' \
  -d '{"scenarioVersionId":"00000000-0000-4000-8000-000000000010"}'
```

POST returns HTTP 201 only after the job is committed. Its relative `Location` header points to the GET endpoint, and its body uses the same public execution representation. Follow that location on port 8000; the job remains available after restarting the API. New jobs remain `queued` until a running worker picks them up (or `process_next_execution()` is invoked explicitly). Each successful POST creates a distinct job.

The request accepts only a scenario-version reference; inputs are loaded from Spring. Unknown scenarios return 404, invalid requests or unsupported scenario inputs return 422, upstream connection/server failures return 503, and malformed upstream responses return 502. Unexpected internal failures return 500 without exposing exception details.

### Python connectivity check

From the repository root:

```bash
PGPASSWORD=execution_local uv run --package algorithm-service python - <<'PY'
from sqlalchemy import text

from algorithm_service.config import Settings
from algorithm_service.database import create_database_engine

engine = create_database_engine(Settings())
try:
    with engine.connect() as connection:
        print(connection.execute(
            text("SELECT current_user, current_database(), current_schema()")
        ).one())
finally:
    engine.dispose()
PY
```

Expected: `('execution_app', 'algorithm_lab', 'executions')`.

## Builds and Checks

### Frontend

From the repository root:

```bash
npm --prefix apps/web run build
npm --prefix apps/web run lint
npm --prefix apps/web run format:check
npm --prefix apps/web test
```

Vitest and React Testing Library run application-shell, catalog, route navigation, direct scenario entry, and execution-creation tests in jsdom. They verify read-only scenario input, pending-button disabling, creation receipts, detail navigation and direct URLs, error states, and no automatic POST retries. Controlled-timer tests verify queued/running polling, stopping on terminal states or request errors, and GET-only manual retries. API tests check runtime validation, HTTP/network/JSON failures, and AbortSignal forwarding. Tests stub fetch and create a fresh QueryClient per render to avoid shared cache state; retry delays are disabled in tests. They do not require running backends or verify an actual browser-to-Spring proxy connection. `npm --prefix apps/web run test:watch` starts watch mode. Prettier checks formatting; use `npm --prefix apps/web run format` to apply it.

The build runs TypeScript checking followed by Vite and writes static assets to `apps/web/dist/`. To inspect that build locally:

```bash
npm --prefix apps/web run preview
```

The preview server is for local verification. Deployment will serve the static build through a web server.

### Python

```bash
uv run ruff check packages/algorithms apps/algorithm-service
uv run mypy packages/algorithms/src apps/algorithm-service/src apps/algorithm-service/tests
uv run --all-packages pytest
uv build --package algorithm-lab
uv build --package algorithm-service
```

`uv build` produces Python distributions in the repository's `dist/` directory. Building the service does not bundle its dependencies; its workspace dependency must also be supplied when installing outside uv's workspace.

pytest runs the service configuration, schema-validation, HTTP-client, and algorithm tests by default. They verify required credentials, environment-variable overrides, password redaction, and URL handling, including generated passwords through Hypothesis. mypy uses the Pydantic plugin to understand settings loaded from the environment.

The synchronous `DataClient` loads scenario versions from Spring using an injected `httpx.Client`. Its tests use `MockTransport`, so Spring does not need to be running. They cover successful reads, HTTP failures, network errors and timeouts, malformed response data, and mismatched scenario IDs. The caller owns the HTTP client's lifecycle; FastAPI now supplies its base URL, a five-second timeout, disabled redirects, and shutdown cleanup.

`ExecutionRepository` persists queued jobs with their scenario reference, algorithm version, and JSONB input snapshot. It commits before returning and can read jobs by UUID, returning `None` for an unknown ID. The internal `Execution` model includes status, attempt, timestamps, and optional result fields. The repository can also reserve one queued job or recover a running job whose lease has expired through `reserve_execution(lease_seconds=30)`. Selection uses `FOR UPDATE SKIP LOCKED` and updates the job in the same short transaction. Reserving sets `running`, increments `attempt`, assigns a database-clock lease deadline, and resets result/error/completion fields for the new attempt. `started_at` refers to the current attempt. A positive lease duration is required; an empty or fully reserved queue returns `None`. Terminal jobs are excluded. The transaction commits before the reservation is returned; computation will happen outside it.

This repository does not call Spring or execute algorithms. `complete_execution()` and `fail_execution()` persist success or failure only for a matching running attempt with a valid lease. They lock the row first, then check `clock_timestamp()` in the guarded update so time is re-evaluated after any lock wait. Accepted updates save duration and finish time and clear the lease; success saves a JSONB result and clears the error, while failure saves the error and clears the result. They return `True` after commit or `False` without changing an ineligible job. `process_next_execution()` in `worker.py` processes at most one job. It reserves work, checks the algorithm and implementation version, validates the stored Fibonacci input, runs the independent function, and uses the guarded completion methods. It returns `idle`, `succeeded`, `failed`, or `discarded`; these are function outcomes rather than additional database statuses. Timing includes input checks and computation but excludes reservation and completion database calls. Exceptions during checks/computation are recorded as internal job errors; database errors during reservation or persistence propagate. A rejected completion is discarded without an unguarded retry or failure fallback. `run_worker()` repeatedly processes jobs, waits interruptibly when idle, and logs SQLAlchemy errors before a separate retry delay. Other unexpected loop errors propagate. Lease renewal is still pending.

Start the worker in its own terminal after installing the workspace packages:

```bash
uv sync --all-packages --frozen
PGPASSWORD=execution_local uv run --package algorithm-service algorithm-worker
```

The same CLI can be invoked as `python -m algorithm_service.worker_cli` through `uv run --package algorithm-service`. Configure timing through `WORKER_POLL_INTERVAL`, `WORKER_ERROR_RETRY_INTERVAL`, and `WORKER_LEASE_SECONDS`; all must be positive and wait intervals must be finite. The worker needs the execution database, not a running Spring service.

Stop with Ctrl+C (`SIGINT`) or send `SIGTERM`. The signal sets a stop event, interrupts polling/error waits, and prevents another iteration after the current one finishes. Current computation and database calls are not forcibly cancelled. The CLI closes the engine and restores previous handlers even if the loop fails. Unexpected startup/loop errors terminate the process rather than being reported as successful jobs.

For the backend acceptance check, stop the worker, POST a job through the API, confirm GET shows `queued`, start the worker, and GET the same URL until it shows `succeeded` and `{"value":55}`. For browser acceptance, start the job on `/showcases/K01` with the worker stopped, confirm the detail page shows `queued`, reload that URL, then start the worker. The page should display result `55` automatically; the short `running` state may fall between polls.

To process one queued or expired job manually from the repository root:

```bash
PGPASSWORD=execution_local uv run --package algorithm-service python - <<'PYWORKER'
from algorithm_service.config import Settings
from algorithm_service.database import create_database_engine
from algorithm_service.repository import ExecutionRepository
from algorithm_service.worker import process_next_execution

engine = create_database_engine(Settings())
try:
    print(process_next_execution(ExecutionRepository(engine)))
finally:
    engine.dispose()
PYWORKER
```

This changes a real job in the development database; it selects the oldest eligible job rather than a requested ID. Spring does not need to be running because inputs are already stored. GET the job afterward to inspect its result or failure status.

`ExecutionService` combines the Spring client and repository: it accepts only showcase `K01`, validates Fibonacci input as a strict integer from 0 through 78, and persists the validated snapshot with algorithm ID `fibonacci.iterative` and implementation version `1`. Invalid scenarios and upstream failures do not create jobs. Existing executions are read without contacting Spring; unknown IDs raise `ExecutionNotFound`. Service tests isolate HTTP and persistence dependencies and verify these behaviors. FastAPI POST/GET routes and application lifecycle are implemented; the single-job processor and continuous worker CLI are available.

Run the PostgreSQL integration tests separately with Docker available:

```bash
uv run --all-packages pytest -m integration
```

Testcontainers creates a disposable PostgreSQL instance on a dynamically assigned port. The migration test applies Alembic, verifies allowed statuses and invalid status/attempt rejection, checks repeated upgrades, and exercises downgrade and recreation. Repository tests verify committed jobs through a separate engine, JSONB snapshots and defaults, unknown IDs, and recovery after a failed insert. Reservation tests cover lease expiry and retry state, skipped row locks, terminal jobs, and concurrent workers contending for one job. Completion tests cover success/failure, expired leases, stale attempts, terminal jobs, competing outcomes, and lease expiry while waiting for a row lock. API integration tests combine real service and repository code with temporary PostgreSQL and simulated Spring HTTP responses. They verify POST/GET persistence across fresh API instances and ensure failed scenario resolution or validation does not persist jobs. Worker integration tests cover the full queued-to-succeeded transition, persisted calculation failure, and discarding an expired result followed by retry recovery. Worker process tests start the installed `algorithm-worker` command against temporary PostgreSQL, process jobs created before and after startup, and check clean exit on both SIGINT and SIGTERM. Unit tests cover polling, database error recovery, interruptible waits, stop-after-current-job, and cleanup after loop or partial startup failure. These tests do not connect to the Compose database or a running Spring instance. To run both unit and integration tests together:

```bash
uv run --all-packages pytest -m ""
```

The algorithm package has no computational implementation yet; add reference and property tests alongside its first algorithms.

### Spring

```bash
cd apps/data-service
./gradlew bootJar
./gradlew ktlintCheck
./gradlew test
```

The executable JAR is written to `apps/data-service/build/libs/`. ktlint checks Kotlin source and Gradle scripts and is included in Gradle's `check` task. Use `./gradlew ktlintFormat` to format them.

The Spring tests use Testcontainers and `@ServiceConnection` to start an isolated PostgreSQL database, initialize the catalog schema, and override application connection details. They check seeded data, scenario immutability, Flyway validation, repeated migration without duplicate entries, and HTTP responses for catalog access, known and unknown scenario versions, and malformed IDs. Docker is required; the Compose database and `PGPASSWORD` are not needed and are not used by these tests.

To force a fresh test run instead of accepting Gradle task up-to-date results:

```bash
./gradlew test --rerun-tasks
```

The first build downloads the wrapper distribution and dependencies. `--offline` works only after all required dependencies have been cached.

## Add Database Migrations

### Ownership rules

Spring/Flyway owns only `catalog`; Python/Alembic owns only `executions`. Neither migration tool should alter the other application's tables. Scenario references in Python are service-level references, not cross-schema foreign keys.

After a migration has been applied to a shared or retained database, preserve it and add another revision. Rewriting the initial migration is appropriate only when all affected development databases are intentionally reset together.

### Flyway

Create the next migration in:

```text
apps/data-service/src/main/resources/db/migration/V2__describe_the_change.sql
```

Use schema-qualified table names such as `catalog.scenario_version`. Start Spring to apply the migration to the development database. The isolated Spring tests verify migrations against their own temporary database. Flyway validates the checksums of previously applied migrations. Do not edit an applied migration or repair its checksum merely to hide an unexpected mismatch.

### Alembic

From `apps/algorithm-service`:

```bash
uv run alembic revision -m "describe the change"
```

Keep the generated revision identifiers, fill in `upgrade()` and `downgrade()`, and explicitly target `schema="executions"` in table and constraint operations.

Then apply and inspect:

```bash
PGPASSWORD=execution_local uv run alembic upgrade head
PGPASSWORD=execution_local uv run alembic current
uv run alembic history
```

`target_metadata` is currently `None`, so write migrations manually. Do not use `--autogenerate` until SQLAlchemy model metadata has been connected to Alembic.

Generate SQL for inspection without connecting to PostgreSQL:

```bash
PGPASSWORD=offline-placeholder uv run alembic upgrade head --sql
```

Configuration currently requires a password even in offline mode; this placeholder is sufficient for SQL generation.

A downgrade can delete data. Exercise it only against disposable data after reviewing the migration. Downgrading the current initial revision drops the execution table:

```bash
PGPASSWORD=execution_local uv run alembic downgrade -1
PGPASSWORD=execution_local uv run alembic upgrade head
```

## Inspect Database State

From the repository root:

```bash
docker compose -f infra/compose.yaml exec postgres \
  psql -U postgres -d algorithm_lab \
  -c 'SELECT version, success FROM catalog.flyway_schema_history;'

docker compose -f infra/compose.yaml exec postgres \
  psql -U postgres -d algorithm_lab \
  -c 'SELECT version_num FROM executions.alembic_version;'

docker compose -f infra/compose.yaml exec postgres \
  psql -U postgres -d algorithm_lab \
  -c 'TABLE catalog.showcase;'
```

Migration-state queries work after the respective migration tool has initialized its schema.

## Stop or Reset Local PostgreSQL

Stop the database while preserving its data:

```bash
docker compose -f infra/compose.yaml down
```

For a complete reset, first stop the running Spring service and any other database clients. The following commands **delete all data in this project's local PostgreSQL volume**, including both schemas and migration histories:

```bash
docker compose -f infra/compose.yaml down --volumes
docker compose -f infra/compose.yaml up -d --wait
```

The initialization script recreates roles and empty schemas. Reapply Alembic:

```bash
cd apps/algorithm-service
PGPASSWORD=execution_local uv run alembic upgrade head
cd ../..
```

Reapply Flyway by starting Spring (the isolated test suite does not migrate the development database):

```bash
cd apps/data-service
PGPASSWORD=catalog_local ./gradlew bootRun
```

After startup has completed, stop Spring with Ctrl+C and return to the root:

```bash
cd ../..
```

The showcase catalog should again contain `K01`, and the execution table should be empty.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Database connection refused | Start Compose, inspect `ps` and logs, and check the host port. |
| Password authentication failed | Use the password and role for the correct service; initialization scripts do not update an existing volume. |
| Python settings report a missing password | Supply `PGPASSWORD` to the command; `.env` is not loaded automatically. |
| Python tries to import `asyncpg` | The configured driver must be `postgresql+psycopg`, matching the installed dependency and synchronous engine. |
| Schema or table does not exist | Verify initialization completed, then apply Flyway or Alembic. |
| Flyway checksum mismatch | Restore the applied migration and add a new one, or intentionally reset disposable local data. |
| Spring tests do not initialize a reset development database | Tests intentionally use a disposable database. Start Spring with `bootRun` to migrate the Compose database. |
| Testcontainers cannot connect to Docker | Ensure the Docker daemon is running and accessible. Integration tests do not silently skip when Docker is unavailable. |
| Gradle cannot find Java 25 | Set `JAVA_HOME` to a JDK 25 installation and check `./gradlew --version`. |
| Docker socket permission denied | Ensure your user can access the configured Docker daemon. |

Inspect PostgreSQL startup errors with:

```bash
docker compose -f infra/compose.yaml logs postgres
```
