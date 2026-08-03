import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, reactive } from 'vue'

const authApi = vi.hoisted(() => ({
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(),
  signOut: vi.fn(),
}))
const routerApi = vi.hoisted(() => ({ replace: vi.fn() }))
const route = reactive({ name: 'today', meta: { showNavigation: true } })

vi.mock('../../src/auth/session.js', () => authApi)
vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => routerApi,
}))

import App from '../../src/App.vue'

function mountApp() {
  return mount(App, {
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
        RouterView: { template: '<div />' },
        AppNavigation: { template: '<nav />' },
      },
    },
  })
}

describe('App feedback entry', () => {
  beforeEach(() => {
    route.name = 'today'
    route.meta = { showNavigation: true }
    authApi.getSession.mockResolvedValue({ access_token: 'token' })
    authApi.onAuthStateChange.mockReturnValue(() => {})
    authApi.signOut.mockResolvedValue(undefined)
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('shows feedback before logout on authenticated business pages', async () => {
    const wrapper = mountApp()
    await flushPromises()

    const buttons = wrapper.findAll('button')
    expect(buttons[0].text()).toBe('反馈')
    expect(buttons[1].text()).toContain('退出登录')
    await buttons[0].trigger('click')
    await nextTick()
    expect(wrapper.text()).toContain('意见反馈')
    wrapper.unmount()
  })

  it('does not show feedback on unauthenticated or meta-hidden pages', async () => {
    authApi.getSession.mockResolvedValue(null)
    const guest = mountApp()
    await flushPromises()
    expect(guest.text()).not.toContain('反馈')
    guest.unmount()

    authApi.getSession.mockResolvedValue({ access_token: 'token' })
    route.name = 'onboarding'
    route.meta = { showNavigation: false }
    const onboarding = mountApp()
    await flushPromises()
    expect(onboarding.text()).not.toContain('反馈')
    onboarding.unmount()
  })

  it('maps only known route names to page_key', async () => {
    route.name = 'unknown'
    const wrapper = mountApp()
    await flushPromises()
    expect(wrapper.find('.feedback-trigger').exists()).toBe(false)
    wrapper.unmount()
  })
})
