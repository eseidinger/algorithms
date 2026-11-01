export const fibonacciScenario = {
  id: '00000000-0000-4000-8000-000000000010',
  scenarioId: '00000000-0000-4000-8000-000000000001',
  showcaseId: 'K01',
  version: 1,
  name: 'Fibonacci with n = 10',
  input: { n: 10 },
}

export const createdExecution = {
  id: '10000000-0000-4000-8000-000000000001',
  scenarioVersionId: fibonacciScenario.id,
  algorithmId: 'fibonacci.iterative',
  implementationVersion: '1',
  status: 'queued',
  input: { n: 10 },
  result: null,
  createdAt: '2026-01-01T00:00:00Z',
  startedAt: null,
  finishedAt: null,
  durationMs: null,
}
