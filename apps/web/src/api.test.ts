import { describe, expect, it, vi } from 'vitest'
import { request } from './api'

describe('API errors', () => {
  it('surfaces the stable server message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, json: async () => ({ error: { message: 'Return window passed' } }) }))
    await expect(request('/api/returns/proposals')).rejects.toThrow('Return window passed')
  })
})
