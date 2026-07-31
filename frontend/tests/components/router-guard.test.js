import { beforeEach, describe, expect, it } from 'vitest'

import router from '../../src/router/index.js'
import { clearUserId, setUserId } from '../../src/utils/user-session.js'

describe('router user guard', () => {
  beforeEach(async () => {
    clearUserId()
    await router.replace('/onboarding')
  })

  it('redirects missing users and allows a valid stored id', async () => {
    await router.push('/history')
    expect(router.currentRoute.value.name).toBe('onboarding')
    expect(router.currentRoute.value.query.next).toBe('/history')

    setUserId(9)
    await router.push('/history')
    expect(router.currentRoute.value.name).toBe('history')
  })
})
