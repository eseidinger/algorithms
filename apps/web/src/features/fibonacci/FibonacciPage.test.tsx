import { act, fireEvent, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { createdExecution, fibonacciScenario } from '../../test/fixtures'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'
import FibonacciPage from './FibonacciPage'

function mockRequests(
  post: () => Promise<Response> = () =>
    Promise.resolve(Response.json(createdExecution, { status: 201 })),
) {
  const fetchMock = vi.fn((url: string, options?: RequestInit) => {
    if (url === `/api/data/scenario-versions/${fibonacciScenario.id}`) {
      return Promise.resolve(Response.json(fibonacciScenario))
    }
    if (url === '/api/algorithms/executions' && options?.method === 'POST') {
      return post()
    }
    throw new Error(`Unexpected request: ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('Fibonacci scenario page', () => {
  it('shows a loading indicator before the scenario arrives', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise<Response>(() => {})),
    )
    renderWithQueryClient(<FibonacciPage />)
    expect(
      screen.getByRole('progressbar', { name: 'Loading scenario' }),
    ).toBeVisible()
    expect(
      screen.queryByRole('button', { name: 'Run Fibonacci' }),
    ).not.toBeInTheDocument()
  })

  it('shows the immutable input without automatically starting an execution', async () => {
    const fetchMock = mockRequests()
    renderWithQueryClient(<FibonacciPage />)
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Fibonacci' }),
    ).toBeVisible()
    expect(screen.getByText('Fibonacci with n = 10')).toBeVisible()
    expect(screen.getByText('Input: n = 10')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Run Fibonacci' })).toBeEnabled()
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()
    expect(
      fetchMock.mock.calls.filter(([, options]) => options?.method === 'POST'),
    ).toHaveLength(0)
  })

  it.each([
    [
      'unknown scenario',
      () => new Response('private details', { status: 404 }),
    ],
    [
      'invalid input',
      () => Response.json({ ...fibonacciScenario, input: { n: true } }),
    ],
    [
      'wrong version ID',
      () => Response.json({ ...fibonacciScenario, id: createdExecution.id }),
    ],
  ])('blocks starting when the scenario has %s', async (_name, response) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() => Promise.resolve(response())),
    )
    renderWithQueryClient(<FibonacciPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load the Fibonacci scenario.',
    )
    expect(
      screen.queryByRole('button', { name: 'Run Fibonacci' }),
    ).not.toBeInTheDocument()
  })

  it('posts the scenario reference once and disables the button while pending', async () => {
    let resolve!: (response: Response) => void
    const pending = new Promise<Response>((respond) => {
      resolve = respond
    })
    const fetchMock = mockRequests(() => pending)
    renderWithQueryClient(<FibonacciPage />)

    fireEvent.click(
      await screen.findByRole('button', { name: 'Run Fibonacci' }),
    )
    const starting = await screen.findByRole('button', { name: 'Starting…' })
    expect(starting).toBeDisabled()
    fireEvent.click(starting)

    const posts = fetchMock.mock.calls.filter(
      ([, options]) => options?.method === 'POST',
    )
    expect(posts).toHaveLength(1)
    expect(posts[0]).toEqual([
      '/api/algorithms/executions',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenarioVersionId: fibonacciScenario.id }),
      },
    ])

    await act(async () => {
      resolve(Response.json(createdExecution, { status: 201 }))
    })
    expect(await screen.findByRole('alert')).toHaveTextContent(
      `Execution created. ID: ${createdExecution.id}`,
    )
    expect(screen.getByRole('button', { name: 'Run Fibonacci' })).toBeEnabled()
  })

  it.each([
    [
      'HTTP error',
      () => Promise.resolve(new Response('private details', { status: 503 })),
    ],
    ['network error', () => Promise.reject(new TypeError('Connection lost'))],
    [
      'invalid receipt',
      () => Promise.resolve(Response.json({ wrong: 'shape' }, { status: 201 })),
    ],
  ])('reports a POST %s without automatic retry', async (_name, post) => {
    const fetchMock = mockRequests(post)
    renderWithQueryClient(<FibonacciPage />)
    fireEvent.click(
      await screen.findByRole('button', { name: 'Run Fibonacci' }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not confirm the execution.',
    )
    expect(
      fetchMock.mock.calls.filter(([, options]) => options?.method === 'POST'),
    ).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Run Fibonacci' })).toBeEnabled()
  })
})
