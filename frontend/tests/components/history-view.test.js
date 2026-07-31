import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../../src/api/recommendation.js', () => ({
  listRecommendationHistory: vi.fn().mockResolvedValue([]),
}))
vi.mock('../../src/api/user.js', () => ({
  getUser: vi.fn().mockResolvedValue({ id: 1, username: '小果' }),
}))
vi.mock('../../src/utils/user-session.js', () => ({
  getUserId: () => 1,
  clearUserId: vi.fn(),
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ replace: vi.fn() }),
}))

import HistoryView from '../../src/views/HistoryView.vue'

describe('HistoryView', () => {
  it('shows an explicit empty state', async () => {
    const wrapper = mount(HistoryView, {
      global: {
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('还没有推荐历史')
    expect(wrapper.text()).toContain('生成第一组今日推荐后')
  })
})
