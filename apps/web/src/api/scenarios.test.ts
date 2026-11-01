import { describe, expect, it, vi } from 'vitest'
import { fibonacciScenario } from '../test/fixtures'
import { getFibonacciScenario } from './scenarios'

describe('Fibonacci scenario API', () => {
  it('loads the seeded scenario and forwards cancellation', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(Response.json(fibonacciScenario))
    vi.stubGlobal('fetch', fetchMock)
    const controller = new AbortController()
    await expect(getFibonacciScenario(controller.signal)).resolves.toEqual(
      fibonacciScenario,
    )
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/data/scenario-versions/00000000-0000-4000-8000-000000000010',
      { signal: controller.signal },
    )
  })

  it('rejects unknown scenarios without leaking backend details', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(new Response('private details', { status: 404 })),
    )
    await expect(getFibonacciScenario()).rejects.toThrow(
      'Could not load the Fibonacci scenario',
    )
  })

  it.each([
    { ...fibonacciScenario, id: '00000000-0000-4000-8000-000000000099' },
    { ...fibonacciScenario, showcaseId: 'K02' },
    { ...fibonacciScenario, version: 0 },
    { ...fibonacciScenario, input: { n: -1 } },
    { ...fibonacciScenario, input: { n: 79 } },
    { ...fibonacciScenario, input: { n: true } },
    { ...fibonacciScenario, input: { n: '10' } },
    {},
  ])('rejects invalid scenario response %#', async (payload) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(payload)))
    await expect(getFibonacciScenario()).rejects.toThrow()
  })

  it('rejects malformed JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('not JSON')))
    await expect(getFibonacciScenario()).rejects.toThrow()
  })
})
