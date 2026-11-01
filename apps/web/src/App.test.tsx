import { fireEvent, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import { fibonacciScenario } from './test/fixtures'
import { renderWithQueryClient } from './test/renderWithQueryClient'

describe('application shell', () => {
  it('provides an accessible shell and displays the loaded catalog', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() =>
        Promise.resolve(
          Response.json([
            {
              id: 'K01',
              name: 'Fibonacci',
              description: 'Explore Fibonacci numbers.',
            },
          ]),
        ),
      ),
    )
    renderWithQueryClient(<App />)

    expect(
      within(screen.getByRole('banner')).getByText('Algorithm Lab'),
    ).toBeVisible()
    expect(
      within(screen.getByRole('main')).getByRole('heading', {
        level: 1,
        name: 'Algorithm Catalog',
      }),
    ).toBeVisible()
    expect(
      await within(screen.getByRole('main')).findByRole('heading', {
        level: 2,
        name: 'Fibonacci',
      }),
    ).toBeVisible()
  })

  it('opens the Fibonacci scenario from its catalog card', async () => {
    const fetchMock = vi.fn((url: string) =>
      Promise.resolve(
        Response.json(
          url === '/api/data/showcases'
            ? [
                {
                  id: 'K01',
                  name: 'Fibonacci',
                  description: 'Explore Fibonacci numbers.',
                },
              ]
            : fibonacciScenario,
        ),
      ),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderWithQueryClient(<App />)
    const link = await screen.findByRole('link', { name: 'Open showcase' })
    expect(link).toHaveAttribute('href', '/showcases/K01')
    fireEvent.click(link)
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Fibonacci' }),
    ).toBeVisible()
    expect(screen.getByText('Input: n = 10')).toBeVisible()
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/data/scenario-versions/${fibonacciScenario.id}`,
      expect.any(Object),
    )
  })

  it('loads the scenario when its URL is opened directly', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(Response.json(fibonacciScenario)),
      )
    vi.stubGlobal('fetch', fetchMock)
    renderWithQueryClient(<App />, ['/showcases/K01'])
    expect(await screen.findByText('Input: n = 10')).toBeVisible()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/data/scenario-versions/${fibonacciScenario.id}`,
      expect.any(Object),
    )
  })

  it('handles unknown routes without requesting the catalog', () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    renderWithQueryClient(<App />, ['/unknown'])
    expect(screen.getByText('Page not found.')).toBeVisible()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
