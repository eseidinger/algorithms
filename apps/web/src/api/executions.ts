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
