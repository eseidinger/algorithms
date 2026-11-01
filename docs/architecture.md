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
| [Reservation and worker scenarios](architecture/worker-scenarios.md) | Sequence diagrams for competing callers, empty queues, lease recovery, and planned guarded worker completion |

Read the current scope below first. For implementation work, follow the relevant contract and data document, then the corresponding scenario. Each scenario identifies its prerequisites, trigger, and expected outcome. A planned participant or message does not imply that its implementation exists.

## Purpose and Current Scope

Algorithm Lab connects independent algorithm implementations with an interactive web application and reproducible data experiments. The first vertical slice uses iterative Fibonacci to establish the path from a versioned scenario to a durable execution and, eventually, a displayed result.

| Component or capability | Current state |
| --- | --- |
| React application | Application shell, MUI theme, router and TanStack Query providers; no backend calls or execution views yet |
| Spring data service | Read-only catalog and immutable scenario-version APIs; Flyway migrations and health endpoints |
| Python algorithm package | Iterative Fibonacci implementation with reference and property tests |
| FastAPI algorithm service | Create and read executions; Spring scenario lookup, validation, persistence, and resource lifecycle |
| Execution reservation | Repository method with expiring leases, attempt tracking, and concurrent reservation protection |
| Worker | Planned: computation, guarded completion, failure handling, and a processing loop |
| Web server / reverse proxy | Planned: serve the static frontend and route requests to both APIs |
| Additional data stores / outbox | Planned in later slices; not dependencies of this slice |

The current API can persist a job as `queued`. Reservation code can transition it to `running`, but there is no running worker that invokes it or stores computed results. The complete browser workflow is not yet available.

## Next Increments and Extension Points

1. Add guarded success/failure persistence and worker execution, including obsolete-attempt rejection.
2. Add the worker loop and verify recovery and processing of jobs submitted while it is stopped.
3. Connect React to catalog/scenario selection, execution creation, polling, and persistent execution URLs. Scenario discovery beyond the current known fixture ID still needs a UI/API decision.
4. Add web-server routing, container packaging, deployment declarations, and migration sequencing.
5. Verify the complete browser workflow.

Later modules can reuse the catalog/version model, durable execution records, and independent algorithm package. Object storage, artifact release contracts, an outbox, and search/graph/vector projections belong to later increments. They are described in the [data stores slice plan](Algorithm_Lab_Data_Stores_Vertical_Slice_Plan.md), not implemented requirements of the current Fibonacci path.
