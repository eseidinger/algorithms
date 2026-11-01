import { z } from 'zod'

const showcaseSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
})

const showcasesSchema = z.array(showcaseSchema)

export type Showcase = z.infer<typeof showcaseSchema>

export async function getShowcases(signal?: AbortSignal): Promise<Showcase[]> {
  const response = await fetch('/api/data/showcases', { signal })

  if (!response.ok) {
    throw new Error(`Catalog request failed (HTTP ${response.status})`)
  }

  return showcasesSchema.parse(await response.json())
}
