import { z } from 'zod'

const createdExecutionSchema = z.object({
  id: z.string().uuid(),
  status: z.literal('queued'),
})

export async function createExecution(scenarioVersionId: string) {
  const response = await fetch('/api/algorithms/executions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ scenarioVersionId }),
  })

  if (!response.ok) {
    throw new Error('Could not start the execution')
  }

  return createdExecutionSchema.parse(await response.json())
}

export const executionIdSchema = z.string().uuid()

const executionSchema = z
  .object({
    id: executionIdSchema,
    scenarioVersionId: z.string().uuid(),
    algorithmId: z.literal('fibonacci.iterative'),
    implementationVersion: z.literal('1'),
    status: z.enum(['queued', 'running', 'succeeded', 'failed', 'cancelled']),
    input: z.object({ n: z.number().int().min(0).max(78) }),
    result: z.object({ value: z.number().int().nonnegative() }).nullable(),
    createdAt: z.iso.datetime({ offset: true }),
    startedAt: z.iso.datetime({ offset: true }).nullable(),
    finishedAt: z.iso.datetime({ offset: true }).nullable(),
    durationMs: z.number().nonnegative().nullable(),
  })
  .refine(
    (execution) =>
      execution.status !== 'succeeded' || execution.result !== null,
    {
      message: 'A successful execution must include a result',
    },
  )

export class ExecutionNotFoundError extends Error {
  constructor() {
    super('Execution not found')
  }
}

export async function getExecution(executionId: string, signal?: AbortSignal) {
  const id = executionIdSchema.parse(executionId)
  const response = await fetch(`/api/algorithms/executions/${id}`, { signal })
  if (response.status === 404) throw new ExecutionNotFoundError()
  if (!response.ok) throw new Error('Could not load the execution')
  const execution = executionSchema.parse(await response.json())
  if (execution.id !== id) throw new Error('Unexpected execution identity')
  return execution
}
