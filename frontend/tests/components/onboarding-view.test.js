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
const routerApi = vi.hoisted(() => ({ replace: vi.fn() }))

vi.mock('../../src/api/fruit.js', () => fruitApi)
vi.mock('../../src/api/user.js', () => userApi)
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => routerApi,
}))

import OnboardingView from '../../src/views/OnboardingView.vue'
import { ApiError } from '../../src/api/http.js'

describe('OnboardingView', () => {
  beforeEach(() => {
    fruitApi.listFruits.mockResolvedValue([
      { id: 1, name: '苹果', taste: '清甜微酸' },
    ])
    userApi.createUser.mockResolvedValue({ id: 7 })
    userApi.getUser.mockRejectedValue(
      new ApiError('用户不存在', { status: 404 }),
    )
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
    expect(wrapper.text()).toContain('基本信息已保存，但水果偏好暂未保存')

    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(userApi.createUser).toHaveBeenCalledTimes(1)
    expect(userApi.updateUser).toHaveBeenCalledTimes(1)
  })

  it('recovers when the profile was created by an earlier request', async () => {
    userApi.createUser.mockRejectedValueOnce(
      new ApiError('当前账号已经创建用户资料', {
        status: 409,
        code: 'http_error',
      }),
    )
    userApi.replaceFruitPreferences.mockResolvedValueOnce([])

    const wrapper = mount(OnboardingView, {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(userApi.updateUser).toHaveBeenCalledTimes(1)
    expect(routerApi.replace).toHaveBeenCalledWith('/')
    expect(wrapper.text()).not.toContain('当前账号已经创建用户资料')
  })

  it('keeps existing-profile mode when preference loading fails', async () => {
    userApi.getUser.mockResolvedValueOnce({
      id: 7,
      username: '小果',
      city: '苏州',
      region: '华东',
      sweet_preference: 0.5,
      sour_preference: 0.5,
      soft_preference: 0.5,
      crisp_preference: 0.5,
      price_level: 2,
      convenience_preference: 0.5,
    })
    userApi.getFruitPreferences.mockRejectedValueOnce(
      new ApiError('偏好读取失败', { status: 503, code: 'http_error' }),
    )

    const wrapper = mount(OnboardingView, {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('更新你的水果档案')
    expect(wrapper.text()).toContain('保存修改')
  })
})
