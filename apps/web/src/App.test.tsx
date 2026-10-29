import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'
import { AppProviders } from './providers'

describe('application shell', () => {
  it('provides a named header and an accessible main catalog heading', () => {
    render(
      <AppProviders>
        <App />
      </AppProviders>,
    )

    expect(
      within(screen.getByRole('banner')).getByText('Algorithm Lab'),
    ).toBeVisible()
    expect(
      within(screen.getByRole('main')).getByRole('heading', {
        level: 1,
        name: 'Algorithm Catalog',
      }),
    ).toBeVisible()
  })
})
