import { beforeEach, describe, expect, it, vi } from 'vitest'

const signOutMock = vi.fn()
const signUpMock = vi.fn()

vi.mock('../../src/auth/supabase.js', () => ({
  getSupabaseClient: () => ({ auth: { signOut: signOutMock, signUp: signUpMock } }),
  isAuthConfigured: () => true,
}))

import { clearLocalSession, signOut, signUp } from '../../src/auth/session.js'

describe('auth session cleanup', () => {
  beforeEach(() => {
    signOutMock.mockReset()
    signOutMock.mockResolvedValue({ error: null })
    signUpMock.mockReset()
    signUpMock.mockResolvedValue({ data: { session: { access_token: 'test-token' } }, error: null })
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

  it('signs up with only email and password', async () => {
    await signUp('fruit@example.com', 'password123')
    expect(signUpMock).toHaveBeenCalledWith({
      email: 'fruit@example.com',
      password: 'password123',
    })
  })
})
