import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

export function renderWithQueryClient(
  ui: ReactElement,
  initialEntries: string[] = ['/'],
) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 0, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  })

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}
