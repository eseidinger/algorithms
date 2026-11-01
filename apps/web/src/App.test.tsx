import { screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
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
})
