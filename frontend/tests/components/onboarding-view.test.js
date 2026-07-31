import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fruitApi = vi.hoisted(() => ({ listFruits: vi.fn() }))
const userApi = vi.hoisted(() => ({
  createUser: vi.fn(),
  getFruitPreferences: vi.fn(),
  getUser: vi.fn(),
  replaceFruitPreferences: vi.fn(),
  updateUser: vi.fn(),
}))
const sessionApi = vi.hoisted(() => ({
  clearUserId: vi.fn(),
  getUserId: vi.fn(),
  setUserId: vi.fn(),
}))
const routerApi = vi.hoisted(() => ({ replace: vi.fn() }))

vi.mock('../../src/api/fruit.js', () => fruitApi)
vi.mock('../../src/api/user.js', () => userApi)
vi.mock('../../src/utils/user-session.js', () => sessionApi)
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => routerApi,
}))

import OnboardingView from '../../src/views/OnboardingView.vue'

describe('OnboardingView', () => {
  beforeEach(() => {
    sessionApi.getUserId.mockReturnValue(null)
    fruitApi.listFruits.mockResolvedValue([
      { id: 1, name: '苹果', taste: '清甜微酸' },
    ])
    userApi.createUser.mockResolvedValue({ id: 7 })
    userApi.updateUser.mockResolvedValue({ id: 7 })
    userApi.replaceFruitPreferences.mockRejectedValue(
      new Error('偏好服务暂时不可用'),
    )
  })

  it('keeps a created user when preference saving fails', async () => {
    const wrapper = mount(OnboardingView, {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    await flushPromises()

    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(userApi.createUser).toHaveBeenCalledTimes(1)
    expect(sessionApi.setUserId).toHaveBeenCalledWith(7)
    expect(wrapper.text()).toContain('基本信息已保存，但水果偏好暂未保存')

    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(userApi.createUser).toHaveBeenCalledTimes(1)
    expect(userApi.updateUser).toHaveBeenCalledTimes(1)
  })
})
