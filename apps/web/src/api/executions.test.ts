import { describe, expect, it, vi } from 'vitest'
import { createdExecution, fibonacciScenario } from '../test/fixtures'
import { createExecution } from './executions'

describe('execution creation API', () => {
  it('posts only the scenario reference and validates the receipt', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(Response.json(createdExecution, { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(createExecution(fibonacciScenario.id)).resolves.toEqual({
      id: createdExecution.id,
      status: 'queued',
    })
    expect(fetchMock).toHaveBeenCalledWith('/api/algorithms/executions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenarioVersionId: fibonacciScenario.id }),
    })
  })

  it.each([404, 422, 502, 503])('rejects HTTP %i', async (status) => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response('private details', { status }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(createExecution(fibonacciScenario.id)).rejects.toThrow(
      'Could not start the execution',
    )
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it.each([
    {},
    { id: 'invalid', status: 'queued' },
    { id: createdExecution.id, status: 'running' },
  ])(
    'rejects invalid receipts %# without repeating the request',
    async (payload) => {
      const fetchMock = vi
        .fn()
        .mockResolvedValue(Response.json(payload, { status: 201 }))
      vi.stubGlobal('fetch', fetchMock)
      await expect(createExecution(fibonacciScenario.id)).rejects.toThrow()
      expect(fetchMock).toHaveBeenCalledTimes(1)
    },
  )

  it('does not repeat a request after a network failure', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValue(new TypeError('Connection lost'))
    vi.stubGlobal('fetch', fetchMock)
    await expect(createExecution(fibonacciScenario.id)).rejects.toThrow(
      'Connection lost',
    )
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
