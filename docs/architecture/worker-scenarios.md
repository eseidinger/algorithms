# Reservation and Worker Scenarios

[Architecture overview](../architecture.md) · [Data and executions](data-and-executions.md) · [HTTP scenarios](request-scenarios.md)

Status: November 1, 2026. **Reservation, lease recovery, and guarded completion/failure are implemented repository behavior.** The background worker loop, algorithm dispatch, heartbeat renewal, and cancellation workflow are not implemented. Diagrams W1–W3 and W5–W6 use repository callers; they do not claim that running workers exist. W4 describes planned worker orchestration around the implemented persistence methods.

## W1. Competing Callers Reserve Different Jobs

**Implemented.** Prerequisites: two queued jobs E1 and E2, with E1 ordered first. Separate callers use independent PostgreSQL connections.

**Trigger:** Both call `reserve_execution()` while the first transaction still owns a row lock.

```mermaid
sequenceDiagram
    participant A as Repository caller A
    participant B as Repository caller B
    participant D as PostgreSQL executions
    A->>D: BEGIN
    A->>D: CTE selection and UPDATE with SKIP LOCKED
    D-->>A: E1 running, attempt 1; row lock retained
    B->>D: BEGIN
    B->>D: CTE selection and UPDATE with SKIP LOCKED
    Note over B,D: E1 is locked, so select E2
    D-->>B: E2 running, attempt 1
    B->>D: COMMIT
    Note over B: Return E2 with active lease
    A->>D: COMMIT
    Note over A: Return E1 with active lease
```

**Outcome:** Each caller receives a different job. If only E1 exists, the competing caller returns `None` instead of receiving E1. After commit, row locks are released; persisted status and lease prevent another caller from immediately reserving the same job.

The selection and update are one SQL statement. Both occur in a short transaction, and no computation is performed inside it. The default lease is 30 seconds.

**Evidence:** [Reservation tests](../../apps/algorithm-service/tests/test_reservations.py) cover an explicitly locked candidate and two concurrent callers contending for one job.

## W2. No Eligible Work Is Available

**Implemented.** Prerequisites: the queue is empty, or all rows are locked, actively leased, or terminal.

**Trigger:** A caller attempts to reserve one job.

```mermaid
sequenceDiagram
    participant C as Repository caller
    participant D as PostgreSQL executions
    C->>D: BEGIN
    C->>D: Select eligible candidate and update if present
    D-->>C: No returned row
    C->>D: COMMIT
    Note over C: reserve_execution returns None
```

**Outcome:** No row is changed and no exception is required. A future worker loop will wait before polling again; that loop is not implemented yet.

Jobs in `succeeded`, `failed`, or `cancelled` are excluded. A running row with a null lease is also not an expired candidate. Nonpositive lease durations raise `ValueError` before a database transaction starts.

**Evidence:** [Empty queue, active lease, terminal-state and locked-row tests](../../apps/algorithm-service/tests/test_reservations.py).

## W3. Recover an Expired Reservation

**Implemented.** Prerequisites: E1 is running with attempt 1. Its first caller stops making progress and its lease expires.

**Trigger:** Another caller reserves work after the deadline.

```mermaid
sequenceDiagram
    participant A as Repository caller A
    participant D as PostgreSQL executions
    participant B as Repository caller B
    A->>D: Reserve E1 and commit
    D-->>A: E1, attempt 1, lease deadline T1
    Note over A: Caller stops or makes no further progress
    Note over D: Database time passes beyond T1
    B->>D: BEGIN
    B->>D: Select expired E1 and UPDATE
    Note over D: Increment attempt to 2 and set new deadline T2
    Note over D: Reset result, error, duration and completion timestamp
    D-->>B: E1, attempt 2, new started_at
    B->>D: COMMIT
    Note over B: Return the newly reserved attempt
```

**Outcome:** E1 becomes available again without an administrator manually requeuing it. `started_at` identifies the current attempt, not necessarily the first attempt. Input snapshot, algorithm identity, and scenario reference remain unchanged.

Reservation does not terminate the old caller. If it resumes, both processes could compute. Completion is guarded separately by ID, attempt, running state, and current lease validity; that persistence protection is implemented.

**Evidence:** [Lease expiry and retry-state test](../../apps/algorithm-service/tests/test_reservations.py) moves the deadline into the past explicitly, avoiding sleeps and wall-clock races.

## W4. Compute and Persist a Successful Result

**Planned; not executable with the current worker implementation, because no worker exists yet.** Prerequisite: a worker entrypoint and algorithm dispatch are added; the guarded completion methods already exist.

**Trigger:** The worker receives a reservation for `fibonacci.iterative`, implementation version `1`, with input n = 10.

```mermaid
sequenceDiagram
    participant W as Future Python worker
    participant R as ExecutionRepository
    participant D as PostgreSQL executions
    participant F as Independent Fibonacci function
    W->>R: reserve_execution
    R->>D: Reserve and commit E1 attempt 1
    D-->>R: Running job with lease
    R-->>W: Execution snapshot
    W->>W: Check algorithm/version and validate snapshot
    Note over W,F: Reservation transaction is already closed
    W->>F: fibonacci(10)
    F-->>W: 55
    W->>W: Measure computation duration
    W->>R: Complete E1 attempt 1 with result value 55
    R->>D: Guarded UPDATE and commit
    Note over R,D: Require ID, attempt, running status and unexpired lease
    D-->>R: Accepted completion
    R-->>W: Completion accepted
```

**Expected outcome:** Status becomes `succeeded`, with structured result `{"value":55}`, completion timestamp, and duration. A failure path should similarly set `failed` only for the current valid attempt. API reads can then expose the saved outcome.

The worker should use the stored input snapshot and should not fetch it again from Spring. Lease renewal/checkpoints and behavior for computation longer than the lease still need implementation decisions. No result transition is implied merely by having reserved the job.

**Evidence:** There is no worker orchestration test yet. The independent [Fibonacci tests](../../packages/algorithms/tests/test_fibonacci.py), [reservation tests](../../apps/algorithm-service/tests/test_reservations.py), and [completion tests](../../apps/algorithm-service/tests/test_completion.py) cover the existing building blocks separately.

## W5. Reject a Late Result from an Obsolete Attempt

**Implemented repository behavior.** Prerequisite: W3 has reassigned E1 to attempt 2. The callers below invoke completion methods directly; worker integration is still planned.

**Trigger:** The old worker resumes and tries to publish the result of attempt 1.

```mermaid
sequenceDiagram
    participant A as Old attempt caller
    participant B as New attempt caller
    participant D as PostgreSQL executions
    Note over A,D: A held attempt 1; its lease expired
    B->>D: Reserve E1 as attempt 2 and commit
    D-->>B: New reservation
    A->>D: Guarded completion WHERE attempt = 1
    D-->>A: Zero updated rows; reject stale result
    Note over D: Attempt 2 remains unchanged
    B->>D: Guarded completion WHERE attempt = 2 and lease valid
    D-->>B: One updated row; commit succeeded
```

**Expected outcome:** The old result cannot overwrite the new attempt. A completion whose lease has expired should also be rejected even if no replacement has reserved the job yet. Unknown, terminal, or otherwise mismatched jobs must not be updated.

The completion tests verify these guards, including rejection of both success and failure updates from obsolete attempts. It provides protection against stale writes, not exactly-once computation. Repeating an algorithm with external side effects would require additional idempotency design; the current pure Fibonacci function has no such effects.

## W6. Lease Expires While Completion Waits for a Row Lock

**Implemented repository behavior.** Prerequisites: a running attempt has a valid lease, and another database transaction holds its row lock.

**Trigger:** A caller starts completion but must wait for that lock.

```mermaid
sequenceDiagram
    participant H as Lock-holding transaction
    participant C as Completion caller
    participant D as PostgreSQL executions
    H->>D: Lock execution row
    C->>D: BEGIN and SELECT FOR UPDATE
    Note over C,D: Wait for row lock
    H->>D: Lease deadline passes or is set to current time
    H->>D: COMMIT and release lock
    D-->>C: Acquire row lock
    C->>D: Guarded UPDATE using clock_timestamp()
    D-->>C: Zero updated rows because lease has expired
    C->>D: COMMIT
    Note over C: Return False without changing result or status
```

**Outcome:** A lease that was valid when the completion transaction began is not automatically valid when the lock becomes available. Both completion methods acquire the lock before evaluating the time-sensitive update and use actual database wall-clock time rather than the fixed transaction-start timestamp.

**Evidence:** [Completion lock-wait tests](../../apps/algorithm-service/tests/test_completion.py) observe the blocked connection in `pg_stat_activity`, expire its lease while the lock is held, then verify rejection for success and failure. No timing sleep is used to simulate expiry; the observer polls with a bounded timeout.

## Planned Browser Acceptance Scenario

Once the worker and frontend are implemented, the acceptance journey is: select a scenario, POST an execution, poll its saved URL until `succeeded`, display 55, then reload the URL and obtain the same stored result. Also submit while the worker is stopped and verify that starting it later processes the durable job. These are acceptance scenarios from the [first slice plan](../Algorithm_Lab_First_Vertical_Slice_Plan.md), not currently available browser behavior.
