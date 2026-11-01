import { act, fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../../App'
import { createdExecution, fibonacciScenario } from '../../test/fixtures'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'

const succeeded = {
  ...createdExecution,
  status: 'succeeded',
  result: { value: 55 },
  durationMs: 0.25,
}
const url = `/executions/${createdExecution.id}`

afterEach(() => {
  vi.useRealTimers()
})

describe('execution detail route', () => {
  it('shows initial loading', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise<Response>(() => {})),
    )
    renderWithQueryClient(<App />, [url])
    expect(
      screen.getByRole('progressbar', { name: 'Loading execution' }),
    ).toBeVisible()
  })

  it('loads an execution directly without requiring previous navigation', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(() => Promise.resolve(Response.json(succeeded)))
    vi.stubGlobal('fetch', fetchMock)
    renderWithQueryClient(<App />, [url])
    expect(await screen.findByText('Result: 55')).toBeVisible()
    expect(screen.getByText('Input: n = 10')).toBeVisible()
    expect(screen.getByText('Duration: 0.25 ms')).toBeVisible()
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/algorithms/executions/${createdExecution.id}`,
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('navigates after creation and fetches the full execution', async () => {
    const fetchMock = vi.fn((request: string) =>
      Promise.resolve(
        Response.json(
          request.startsWith('/api/data/')
            ? fibonacciScenario
            : request.endsWith(createdExecution.id)
              ? succeeded
              : { id: createdExecution.id, status: 'queued' },
        ),
      ),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderWithQueryClient(<App />, ['/showcases/K01'])
    fireEvent.click(
      await screen.findByRole('button', { name: 'Run Fibonacci' }),
    )
    expect(await screen.findByText('Result: 55')).toBeVisible()
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock).toHaveBeenLastCalledWith(
      `/api/algorithms/executions/${createdExecution.id}`,
      expect.any(Object),
    )
  })

  it('rejects invalid IDs without fetching', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    renderWithQueryClient(<App />, ['/executions/invalid'])
    expect(screen.getByRole('alert')).toHaveTextContent('Invalid execution ID.')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it.each([
    [
      'not found',
      () => Promise.resolve(new Response(null, { status: 404 })),
      'Execution not found.',
    ],
    [
      'server error',
      () => Promise.resolve(new Response(null, { status: 503 })),
      'Could not load the execution.',
    ],
    [
      'network error',
      () => Promise.reject(new TypeError('Offline')),
      'Could not load the execution.',
    ],
    [
      'invalid data',
      () => Promise.resolve(Response.json({})),
      'Could not load the execution.',
    ],
  ])(
    'allows a GET retry after %s without creating another job',
    async (_name, response, message) => {
      const fetchMock = vi
        .fn()
        .mockImplementationOnce(response)
        .mockImplementation(() => Promise.resolve(Response.json(succeeded)))
      vi.stubGlobal('fetch', fetchMock)
      renderWithQueryClient(<App />, [url])
      expect(await screen.findByRole('alert')).toHaveTextContent(message)
      expect(fetchMock).toHaveBeenCalledTimes(1)
      fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
      expect(await screen.findByText('Result: 55')).toBeVisible()
      expect(fetchMock).toHaveBeenCalledTimes(2)
      for (const [request, options] of fetchMock.mock.calls) {
        expect(request).toBe(
          `/api/algorithms/executions/${createdExecution.id}`,
        )
        expect(options).not.toHaveProperty('method', 'POST')
      }
    },
  )

  it.each(['succeeded', 'failed', 'cancelled'])(
    'polls queued and running, then stops on %s',
    async (status) => {
      vi.useFakeTimers()
      const fetchMock = vi
        .fn()
        .mockImplementationOnce(() =>
          Promise.resolve(Response.json(createdExecution)),
        )
        .mockImplementationOnce(() =>
          Promise.resolve(
            Response.json({ ...createdExecution, status: 'running' }),
          ),
        )
        .mockImplementation(() =>
          Promise.resolve(
            Response.json(
              status === 'succeeded'
                ? succeeded
                : { ...createdExecution, status },
            ),
          ),
        )
      vi.stubGlobal('fetch', fetchMock)
      const view = renderWithQueryClient(<App />, [url])
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10)
      })
      expect(screen.getByText('Waiting for a worker.')).toBeVisible()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000)
      })
      expect(screen.getByText('Calculation running.')).toBeVisible()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000)
      })
      expect(
        screen.getByText(
          status === 'succeeded'
            ? 'Result: 55'
            : status === 'failed'
              ? 'Execution failed.'
              : 'Execution cancelled.',
        ),
      ).toBeVisible()
      expect(fetchMock).toHaveBeenCalledTimes(3)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000)
      })
      expect(fetchMock).toHaveBeenCalledTimes(3)
      view.unmount()
    },
  )

  it('stops polling after a background request fails', async () => {
    vi.useFakeTimers()
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() =>
        Promise.resolve(Response.json(createdExecution)),
      )
      .mockRejectedValue(new TypeError('Offline'))
    vi.stubGlobal('fetch', fetchMock)
    const view = renderWithQueryClient(<App />, [url])
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10)
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Could not load the execution.',
    )
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    view.unmount()
  })
})
