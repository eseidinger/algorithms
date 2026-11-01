import { z } from 'zod'

export const FIBONACCI_SCENARIO_VERSION_ID =
  '00000000-0000-4000-8000-000000000010'

const fibonacciScenarioSchema = z.object({
  id: z.literal(FIBONACCI_SCENARIO_VERSION_ID),
  scenarioId: z.string().uuid(),
  showcaseId: z.literal('K01'),
  version: z.number().int().positive(),
  name: z.string(),
  input: z.object({
    n: z.number().int().min(0).max(78),
  }),
})

export async function getFibonacciScenario(signal?: AbortSignal) {
  const response = await fetch(
    `/api/data/scenario-versions/${FIBONACCI_SCENARIO_VERSION_ID}`,
    { signal },
  )

  if (!response.ok) {
    throw new Error('Could not load the Fibonacci scenario')
  }

  return fibonacciScenarioSchema.parse(await response.json())
}
