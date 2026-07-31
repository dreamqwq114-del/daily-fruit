import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const authApi = vi.hoisted(() => ({
  signInWithPassword: vi.fn(),
  signUp: vi.fn(),
}))
const routerApi = vi.hoisted(() => ({ replace: vi.fn() }))
const routeApi = vi.hoisted(() => ({ query: {} }))

vi.mock('../../src/auth/session.js', () => authApi)
vi.mock('../../src/auth/supabase.js', () => ({ isAuthConfigured: () => true }))
vi.mock('vue-router', () => ({
  useRoute: () => routeApi,
  useRouter: () => routerApi,
}))

import LoginView from '../../src/views/LoginView.vue'

async function enterSignup(wrapper) {
  await wrapper.find('.auth-switch').trigger('click')
  await wrapper.find('input[type="email"]').setValue('fruit@example.com')
  await wrapper.find('input[type="password"]').setValue('password123')
}

describe('LoginView', () => {
  beforeEach(() => {
    routeApi.query = {}
    routerApi.replace.mockReset()
    authApi.signInWithPassword.mockReset()
    authApi.signUp.mockReset()
  })

  it('goes directly to onboarding when signup returns a session', async () => {
    authApi.signUp.mockResolvedValue({ session: { access_token: 'test-token' } })
    const wrapper = mount(LoginView)
    await enterSignup(wrapper)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(authApi.signUp).toHaveBeenCalledWith('fruit@example.com', 'password123')
    expect(routerApi.replace).toHaveBeenCalledWith('/onboarding')
    expect(wrapper.text()).not.toContain('打开邮箱确认')
  })

  it('shows a configuration error when signup has no session', async () => {
    authApi.signUp.mockResolvedValue({ session: null })
    const wrapper = mount(LoginView)
    await enterSignup(wrapper)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('注册配置异常，请稍后重试。')
    expect(routerApi.replace).not.toHaveBeenCalled()
  })

  it('keeps the existing login destination', async () => {
    authApi.signInWithPassword.mockResolvedValue({ session: { access_token: 'test-token' } })
    const wrapper = mount(LoginView)
    await wrapper.find('input[type="email"]').setValue('fruit@example.com')
    await wrapper.find('input[type="password"]').setValue('password123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(routerApi.replace).toHaveBeenCalledWith('/')
  })

  it('translates common Supabase errors into Chinese', async () => {
    authApi.signInWithPassword.mockRejectedValue({ code: 'invalid_credentials' })
    const wrapper = mount(LoginView)
    await wrapper.find('input[type="email"]').setValue('fruit@example.com')
    await wrapper.find('input[type="password"]').setValue('password123')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('邮箱或密码错误。')
  })
})
