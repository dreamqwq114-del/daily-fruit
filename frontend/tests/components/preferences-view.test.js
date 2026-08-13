import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const fruitApi = vi.hoisted(() => ({ listFruits: vi.fn() }))
const userApi = vi.hoisted(() => ({
  getFruitPreferences: vi.fn(),
  getUser: vi.fn(),
  replaceFruitPreferences: vi.fn(),
  updateUser: vi.fn(),
}))
const routerApi = vi.hoisted(() => ({ replace: vi.fn() }))

vi.mock('../../src/api/fruit.js', () => fruitApi)
vi.mock('../../src/api/user.js', () => userApi)
vi.mock('vue-router', () => ({
  useRouter: () => routerApi,
}))

import PreferencesView from '../../src/views/PreferencesView.vue'

const user = {
  id: 7,
  username: '曦曦',
  city: 'UNKNOWN',
  region: '华东',
  sweet_preference: 0.9,
  sour_preference: 0.2,
  soft_preference: 0.9,
  crisp_preference: 0,
  texture_preference: 0.8,
  price_level: 2,
  convenience_preference: 0.9,
  discovery_level: 1,
  consumption_horizon_days: 4,
  market_access_level: 2,
  accepts_online_purchase: false,
}

function mountPreferences() {
  return mount(PreferencesView, {
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
      },
    },
  })
}

describe('PreferencesView fruit preference saving', () => {
  beforeEach(() => {
    fruitApi.listFruits.mockResolvedValue([
      { id: 1, name: '苹果', taste: '清甜微酸' },
      { id: 2, name: '香蕉', taste: '香甜绵软' },
    ])
    userApi.getUser.mockResolvedValue(user)
    userApi.getFruitPreferences.mockResolvedValue([])
    userApi.updateUser.mockResolvedValue(user)
    userApi.replaceFruitPreferences.mockResolvedValue([])
  })

  it('locks background navigation while the picker is open and restores it on close', async () => {
    const wrapper = mountPreferences()
    await flushPromises()

    await wrapper.find('.button--small').trigger('click')
    expect(document.body.classList.contains('fruit-picker-is-open')).toBe(true)
    expect(wrapper.find('.fruit-picker-scroll-area').exists()).toBe(true)

    await wrapper.find('.fruit-picker-header .icon-button').trigger('click')
    expect(document.body.classList.contains('fruit-picker-is-open')).toBe(false)
  })

  it('submits the confirmed fruit selection after the profile update', async () => {
    const wrapper = mountPreferences()
    await flushPromises()

    await wrapper.find('.button--small').trigger('click')
    await wrapper.find('.fruit-picker-option-main').trigger('click')
    await wrapper.find('.fruit-picker-actions .button--primary').trigger('click')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(userApi.updateUser).toHaveBeenCalledTimes(1)
    expect(userApi.replaceFruitPreferences).toHaveBeenCalledWith([
      {
        fruit_id: 1,
        preference_score: 2,
        is_forbidden: false,
        has_tried: true,
      },
    ])
    expect(userApi.updateUser.mock.invocationCallOrder[0]).toBeLessThan(
      userApi.replaceFruitPreferences.mock.invocationCallOrder[0],
    )
    expect(wrapper.text()).toContain('偏好已经保存')
  })

  it('ignores a duplicate submit while the first save is in progress', async () => {
    const wrapper = mountPreferences()
    await flushPromises()

    const firstSubmit = wrapper.find('form').trigger('submit')
    const secondSubmit = wrapper.find('form').trigger('submit')
    await Promise.all([firstSubmit, secondSubmit])
    await flushPromises()

    expect(userApi.updateUser).toHaveBeenCalledTimes(1)
    expect(userApi.replaceFruitPreferences).toHaveBeenCalledTimes(1)
  })

  it('retries an explicit null clear after a failed profile update', async () => {
    userApi.updateUser
      .mockRejectedValueOnce(new Error('资料服务暂时不可用'))
      .mockResolvedValueOnce(user)
    const wrapper = mountPreferences()
    await flushPromises()

    const textureField = wrapper
      .find('input[name="texture_preference"]')
      .element.closest('.range-field')
    await textureField.querySelector('button.range-clear').click()
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(userApi.updateUser).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({ texture_preference: null }),
    )
    expect(wrapper.text()).toContain('资料服务暂时不可用')

    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(userApi.updateUser).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ texture_preference: null }),
    )
    expect(wrapper.text()).toContain('偏好已经保存')
  })
})
