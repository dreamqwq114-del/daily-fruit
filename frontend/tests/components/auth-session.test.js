import { beforeEach, describe, expect, it, vi } from 'vitest'

const signOutMock = vi.fn()

vi.mock('../../src/auth/supabase.js', () => ({
  getSupabaseClient: () => ({ auth: { signOut: signOutMock } }),
  isAuthConfigured: () => true,
}))

import { clearLocalSession, signOut } from '../../src/auth/session.js'

describe('auth session cleanup', () => {
  beforeEach(() => {
    signOutMock.mockReset()
    signOutMock.mockResolvedValue({ error: null })
  })

  it('uses the server-backed default scope for an explicit sign out', async () => {
    await signOut()
    expect(signOutMock).toHaveBeenCalledWith()
  })

  it('uses local cleanup only after an API authentication failure', async () => {
    await clearLocalSession()
    expect(signOutMock).toHaveBeenCalledWith({ scope: 'local' })
  })

  it('surfaces an auth service error to the caller', async () => {
    signOutMock.mockResolvedValueOnce({ error: new Error('auth unavailable') })
    await expect(signOut()).rejects.toThrow('auth unavailable')
  })
})
