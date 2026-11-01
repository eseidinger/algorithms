import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'
import CatalogPage from './CatalogPage'

describe('catalog page', () => {
  it('shows an accessible loading indicator while the request is pending', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise<Response>(() => {})),
    )
    renderWithQueryClient(<CatalogPage />)
    expect(
      screen.getByRole('progressbar', { name: 'Loading catalog' }),
    ).toBeVisible()
  })

  it('shows catalog names and descriptions', async () => {
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
            { id: 'K02', name: 'Maze', description: 'Explore graph search.' },
          ]),
        ),
      ),
    )
    renderWithQueryClient(<CatalogPage />)
    expect(
      await screen.findByRole('heading', { level: 2, name: 'Fibonacci' }),
    ).toBeVisible()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Maze' }),
    ).toBeVisible()
    expect(screen.getByText('Explore Fibonacci numbers.')).toBeVisible()
    expect(screen.getByText('Explore graph search.')).toBeVisible()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('handles an empty catalog', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() => Promise.resolve(Response.json([]))),
    )
    renderWithQueryClient(<CatalogPage />)
    expect(await screen.findByText('No showcases available.')).toBeVisible()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it.each([
    ['HTTP failure', () => new Response('private details', { status: 500 })],
    ['malformed JSON', () => new Response('not JSON')],
    ['invalid shape', () => Response.json({ wrong: 'shape' })],
  ])('shows a readable error for %s', async (_name, response) => {
    const fetchMock = vi
      .fn()
      .mockImplementation(() => Promise.resolve(response()))
    vi.stubGlobal('fetch', fetchMock)
    renderWithQueryClient(<CatalogPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load the catalog. Please try again later.',
    )
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(screen.queryByText('private details')).not.toBeInTheDocument()
  })
})
