import { describe, expect, it, vi } from 'vitest'
import { createdExecution, fibonacciScenario } from '../test/fixtures'
import {
  createExecution,
  getExecution,
  ExecutionNotFoundError,
} from './executions'

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

describe('execution reads', () => {
  it('loads a validated execution and forwards cancellation', async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json(createdExecution))
    vi.stubGlobal('fetch', fetchMock)
    const signal = new AbortController().signal
    await expect(getExecution(createdExecution.id, signal)).resolves.toEqual(
      createdExecution,
    )
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/algorithms/executions/${createdExecution.id}`,
      { signal },
    )
  })

  it('rejects an invalid ID before making a request', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    await expect(getExecution('invalid')).rejects.toThrow()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('distinguishes not found from other HTTP failures', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(null, { status: 404 })),
    )
    await expect(getExecution(createdExecution.id)).rejects.toBeInstanceOf(
      ExecutionNotFoundError,
    )
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(null, { status: 500 })),
    )
    await expect(getExecution(createdExecution.id)).rejects.toThrow(
      'Could not load the execution',
    )
  })

  it.each([
    { ...createdExecution, id: fibonacciScenario.id },
    { ...createdExecution, status: 'unknown' },
    { ...createdExecution, status: 'succeeded', result: null },
    { ...createdExecution, result: { value: '55' } },
    { ...createdExecution, durationMs: -1 },
    { ...createdExecution, createdAt: 'yesterday' },
  ])('rejects malformed or mismatched execution %#', async (payload) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(payload)))
    await expect(getExecution(createdExecution.id)).rejects.toThrow()
  })

  it('propagates network and invalid JSON failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Offline')))
    await expect(getExecution(createdExecution.id)).rejects.toThrow('Offline')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{')))
    await expect(getExecution(createdExecution.id)).rejects.toThrow()
  })
})
