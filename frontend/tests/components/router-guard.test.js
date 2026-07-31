import { beforeEach, describe, expect, it, vi } from 'vitest'

const authApi = vi.hoisted(() => ({ isAuthenticated: vi.fn() }))
vi.mock('../../src/auth/session.js', () => authApi)

import router from '../../src/router/index.js'

describe('router auth guard', () => {
  beforeEach(async () => {
    authApi.isAuthenticated.mockResolvedValue(false)
    await router.replace('/login')
  })

  it('redirects guests and allows an authenticated session', async () => {
    await router.push('/history')
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.next).toBe('/history')

    authApi.isAuthenticated.mockResolvedValue(true)
    await router.push('/history')
    expect(router.currentRoute.value.name).toBe('history')
  })
})
