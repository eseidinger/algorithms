# Algorithm Lab Architecture

This is the entry point to the architecture documentation. Status: November 1, 2026. Detailed responsibilities, contracts, and scenarios are maintained in separate documents so they can evolve independently.

See [Local Development](development.md) for installation, startup, builds, tests, and migration commands. The [first vertical slice plan](Algorithm_Lab_First_Vertical_Slice_Plan.md) defines the delivery goal; the [extended project plan](Algorithm_Lab_Project_Plan_Extended_Tech_Stack.md) describes the broader target architecture.

## Documentation Map

| Document | Contents |
| --- | --- |
| [Components and runtime](architecture/components-and-runtime.md) | Component diagram, module responsibilities, local and planned deployment topology, verification strategy |
| [Data and executions](architecture/data-and-executions.md) | Ownership, entity relationships, scenario identity, execution state, leases, and migrations |
| [HTTP contracts](architecture/http-api.md) | Implemented endpoints, request/response representation, status codes, and compatibility behavior |
| [HTTP scenarios](architecture/request-scenarios.md) | Sequence diagrams for catalog access, creation, validation, upstream/storage errors, and reads after restart |
| [Reservation and worker scenarios](architecture/worker-scenarios.md) | Sequence diagrams for competing callers, empty queues, lease recovery, guarded completion, single-job processing, and worker lifecycle |

Read the current scope below first. For implementation work, follow the relevant contract and data document, then the corresponding scenario. Each scenario identifies its prerequisites, trigger, and expected outcome. A planned participant or message does not imply that its implementation exists.

## Purpose and Current Scope

Algorithm Lab connects independent algorithm implementations with an interactive web application and reproducible data experiments. The first vertical slice uses iterative Fibonacci to establish the path from a versioned scenario to a durable execution and, eventually, a displayed result.

| Component or capability | Current state |
| --- | --- |
| React application | Catalog fetched from Spring via Vite proxy and validated with Zod; loading/empty/error states; scenario and execution views pending |
| Spring data service | Read-only catalog and immutable scenario-version APIs; Flyway migrations and health endpoints |
| Python algorithm package | Iterative Fibonacci implementation with reference and property tests |
| FastAPI algorithm service | Create and read executions; Spring scenario lookup, validation, persistence, and resource lifecycle |
| Execution reservation | Repository method with expiring leases, attempt tracking, and concurrent reservation protection |
| Execution completion | Repository methods for guarded success/failure, including lease checks after row-lock waits |
| Worker function | Processes one job, validates algorithm/version/input, computes Fibonacci, and records or discards the outcome |
| Worker process | Separate CLI with continuous polling, database-error retry delay, cooperative SIGINT/SIGTERM shutdown, and resource cleanup |
| Web server / reverse proxy | Planned: serve the static frontend and route requests to both APIs |
| Additional data stores / outbox | Planned in later slices; not dependencies of this slice |

The current API can persist a job as `queued`. Repository code can transition it to `running` and then to `succeeded` or `failed`, and `process_next_execution()` now combines these operations with computation. The separate `algorithm-worker` CLI now runs this processing continuously when started. The complete browser workflow is not yet available.

## Next Increments and Extension Points

1. Extend the connected React catalog with scenario selection, execution creation, polling, and persistent execution URLs. Scenario discovery beyond the current known fixture ID still needs a UI/API decision.
2. Add web-server routing, container packaging, deployment declarations, and migration sequencing.
3. Verify the complete browser workflow.

Later modules can reuse the catalog/version model, durable execution records, and independent algorithm package. Object storage, artifact release contracts, an outbox, and search/graph/vector projections belong to later increments. They are described in the [data stores slice plan](Algorithm_Lab_Data_Stores_Vertical_Slice_Plan.md), not implemented requirements of the current Fibonacci path.
