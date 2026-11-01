# HTTP API Contracts

[Architecture overview](../architecture.md)

Status: November 1, 2026. Implemented behavior and planned extensions are distinguished explicitly.

## HTTP Contracts

### Spring: `/api/data`

| Method and path | Successful response | Relevant failures |
| --- | --- | --- |
| `GET /showcases` | `200`, ordered list of showcase objects | Unexpected storage failures |
| `GET /scenario-versions/{id}` | `200`, version metadata and structured input | `404` unknown UUID; `400` malformed UUID |

Spring also exposes Actuator health and readiness endpoints. There are no scenario creation or update endpoints yet.

### FastAPI: `/api/algorithms`

| Method and path | Successful response | Relevant failures |
| --- | --- | --- |
| `POST /executions` | `201`, execution representation and relative `Location` | `422` invalid request or unsupported inputs; `404` unknown scenario; `503` upstream unavailable; `502` invalid upstream response |
| `GET /executions/{execution_id}` | `200`, persisted execution representation | `404` unknown execution; `422` malformed UUID |

POST accepts a scenario reference:

```json
{
  "scenarioVersionId": "00000000-0000-4000-8000-000000000010"
}
```

Request models reject extra fields. Their alias configuration also accepts Python-style field names; responses are serialized with camelCase names.

`ExecutionResponse` explicitly maps the internal `input_snapshot` to public `input`. It exposes identity, algorithm/version, status, input, result, and creation/start/finish/duration fields. Internal attempt, lease, and error fields are not included.

Each successful POST creates a distinct execution; no idempotency key or request deduplication is implemented. Unexpected internal errors remain server errors rather than being converted to success. FastAPI publishes `/docs` and `/openapi.json`; Spring OpenAPI generation is not configured yet.

See [HTTP scenarios](request-scenarios.md) for successful requests, validation, upstream failures, transaction failure, and restart behavior. The API contracts describe current behavior; guarded completion and planned worker execution are covered separately in [worker scenarios](worker-scenarios.md).
