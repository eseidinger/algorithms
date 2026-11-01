import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'

export function renderWithQueryClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 0, gcTime: 0 },
    },
  })

  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}
