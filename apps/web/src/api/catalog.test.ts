import { describe, expect, it, vi } from 'vitest'
import { getShowcases } from './catalog'

describe('catalog API', () => {
  it('loads and validates the catalog and forwards the abort signal', async () => {
    const showcases = [
      {
        id: 'K01',
        name: 'Fibonacci',
        description: 'Explore Fibonacci numbers.',
      },
    ]
    const fetchMock = vi.fn().mockResolvedValue(Response.json(showcases))
    vi.stubGlobal('fetch', fetchMock)
    const controller = new AbortController()

    await expect(getShowcases(controller.signal)).resolves.toEqual(showcases)
    expect(fetchMock).toHaveBeenCalledWith('/api/data/showcases', {
      signal: controller.signal,
    })
  })

  it('accepts an empty catalog', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json([])))
    await expect(getShowcases()).resolves.toEqual([])
  })

  it('rejects HTTP errors without exposing the response body', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response('private database details', { status: 503 }),
        ),
    )
    await expect(getShowcases()).rejects.toThrow(
      'Catalog request failed (HTTP 503)',
    )
  })

  it.each([
    null,
    {},
    [{ id: 1, name: 'Fibonacci', description: 'Description' }],
    [{ id: 'K01', name: 'Fibonacci' }],
  ])('rejects invalid catalog data %#', async (payload) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(payload)))
    await expect(getShowcases()).rejects.toThrow()
  })

  it('rejects malformed JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('not JSON')))
    await expect(getShowcases()).rejects.toThrow()
  })

  it('preserves network failures', async () => {
    const error = new TypeError('Network unavailable')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
    await expect(getShowcases()).rejects.toBe(error)
  })

  it('preserves cancellation', async () => {
    const error = new DOMException('Request aborted', 'AbortError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
    await expect(getShowcases()).rejects.toBe(error)
  })
})
