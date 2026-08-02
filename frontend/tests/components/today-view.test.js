import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const recommendationApi = vi.hoisted(() => ({
  getTodayRecommendation: vi.fn(),
  refreshRecommendation: vi.fn(),
  submitFeedback: vi.fn(),
}))
const userApi = vi.hoisted(() => ({ getUser: vi.fn() }))
const routerApi = vi.hoisted(() => ({ replace: vi.fn() }))

vi.mock('../../src/api/recommendation.js', () => recommendationApi)
vi.mock('../../src/api/user.js', () => userApi)
vi.mock('vue-router', () => ({
  useRouter: () => routerApi,
}))

import { ApiError } from '../../src/api/http.js'
import TodayView from '../../src/views/TodayView.vue'

function makeRecommendation(id = 10, refreshNumber = 0) {
  const fruit = (fruitId, name) => ({
    id: fruitId,
    code: fruitId === 1 ? 'apple' : 'orange',
    name,
    category: '演示水果',
    taste: '清甜',
    sweet_score: 0.5,
    sour_score: 0.5,
    soft_score: 0.5,
    crisp_score: 0.5,
    convenience_score: 0.8,
    average_price_level: 2,
    default_portion: '1份',
    image_url: null,
    description: `${name}说明`,
    is_active: true,
    nutrition: null,
    seasons: [],
  })

  return {
    id,
    user_id: 1,
    recommendation_date: '2026-07-31',
    refresh_number: refreshNumber,
    total_score: 0.8,
    status: 'active',
    items: [
      {
        id: id * 10 + 1,
        recommendation_id: id,
        fruit_id: 1,
        score: 0.8,
        rank: 1,
        daily_fact: {
          id: 501,
          fruit_id: 1,
          fact_type: 'botany',
          fact_text: '测试冷知识文案',
          sort_order: 1,
          is_active: true,
        },
        fruit: fruit(1, '苹果'),
        reasons: [
          { code: 'in_season', component: 'season_score', message: '当前处于适宜购买月份' },
          { code: 'price_match', component: 'price_match_score', message: '符合你的价格范围' },
        ],
        feedback: [],
      },
      {
        id: id * 10 + 2,
        recommendation_id: id,
        fruit_id: 2,
        score: 0.72,
        rank: 2,
        fruit: fruit(2, '橙子'),
        reasons: [
          { code: 'nutrition_complement', component: 'complement_score', message: '与首选水果营养特点互补' },
          { code: 'convenient', component: 'convenience_score', message: '食用较为方便' },
        ],
        feedback: [],
      },
    ],
  }
}

function mountToday() {
  return mount(TodayView, {
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
      },
    },
  })
}

describe('TodayView', () => {
  beforeEach(() => {
    userApi.getUser.mockResolvedValue({
      id: 1,
      username: '小果',
      region: '华东',
    })
    recommendationApi.getTodayRecommendation.mockResolvedValue(makeRecommendation())
    recommendationApi.refreshRecommendation.mockResolvedValue(makeRecommendation(11, 1))
    recommendationApi.submitFeedback.mockResolvedValue({
      id: 99,
      recommendation_item_id: 101,
      user_id: 1,
      feedback_type: 'eaten',
      comment: '',
    })
  })

  it('renders exactly two ranked fruit cards', async () => {
    const wrapper = mountToday()
    await flushPromises()

    expect(wrapper.findAll('.fruit-card')).toHaveLength(2)
    expect(wrapper.text()).toContain('苹果')
    expect(wrapper.text()).toContain('橙子')
    expect(wrapper.text()).toContain('华东')
  })

  it('renders an optional daily fact after the description', async () => {
    const wrapper = mountToday()
    await flushPromises()

    const firstCard = wrapper.findAll('.fruit-card')[0]
    expect(firstCard.find('.fruit-fact').exists()).toBe(true)
    expect(firstCard.find('.fruit-fact').text()).toContain('每日冷知识')
    expect(firstCard.find('.fruit-fact').text()).toContain('测试冷知识文案')
    expect(
      firstCard.find('.fruit-description').element.compareDocumentPosition(
        firstCard.find('.fruit-fact').element,
      ) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('prevents duplicate refresh and feedback submissions', async () => {
    const wrapper = mountToday()
    await flushPromises()

    let resolveRefresh
    recommendationApi.refreshRecommendation.mockReturnValue(
      new Promise((resolve) => {
        resolveRefresh = resolve
      }),
    )
    const refreshButton = wrapper.find('.refresh-panel button')
    await refreshButton.trigger('click')
    await refreshButton.trigger('click')
    expect(recommendationApi.refreshRecommendation).toHaveBeenCalledTimes(1)
    resolveRefresh(makeRecommendation(11, 1))
    await flushPromises()

    let resolveFeedback
    recommendationApi.submitFeedback.mockReturnValue(
      new Promise((resolve) => {
        resolveFeedback = resolve
      }),
    )
    const feedbackButton = wrapper.find('.feedback-button')
    await feedbackButton.trigger('click')
    await feedbackButton.trigger('click')
    expect(recommendationApi.submitFeedback).toHaveBeenCalledTimes(1)
    resolveFeedback({
      id: 99,
      recommendation_item_id: 111,
      user_id: 1,
      feedback_type: 'eaten',
      comment: '',
    })
    await flushPromises()
  })

  it('redirects to onboarding when the profile is missing', async () => {
    userApi.getUser.mockRejectedValueOnce(
      new ApiError('请求的资源不存在', { status: 404, code: 'http_error' }),
    )
    const wrapper = mountToday()
    await flushPromises()

    expect(routerApi.replace).toHaveBeenCalledWith('/onboarding')
    expect(wrapper.find('.state-card--error').exists()).toBe(false)
  })

  it('keeps the page for temporary database failures', async () => {
    userApi.getUser.mockRejectedValueOnce(
      new ApiError('数据库服务暂时不可用', { status: 503, code: 'http_error' }),
    )
    const wrapper = mountToday()
    await flushPromises()

    expect(routerApi.replace).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('数据库服务暂时不可用')
  })

  it('does not treat a recommendation 404 as a missing profile', async () => {
    recommendationApi.getTodayRecommendation.mockRejectedValueOnce(
      new ApiError('当前没有可用推荐', { status: 404, code: 'http_error' }),
    )
    const wrapper = mountToday()
    await flushPromises()

    expect(routerApi.replace).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('当前没有可用推荐')
  })
})
