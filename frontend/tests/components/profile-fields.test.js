import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ProfileFields from '../../src/components/ProfileFields.vue'
import { createDefaultProfile } from '../../src/utils/fruit-preferences.js'

describe('ProfileFields', () => {
  it('keeps discovery inside basic information and exposes the supported controls', () => {
    const model = createDefaultProfile()
    const wrapper = mount(ProfileFields, {
      props: { modelValue: model },
    })

    expect(wrapper.find('input[name="city"]').exists()).toBe(false)
    expect(wrapper.find('input[name="username"]').exists()).toBe(true)
    expect(wrapper.findAll('select[name="region"] option')).toHaveLength(8)
    expect(wrapper.findAll('input[type="range"]')).toHaveLength(5)
    expect(wrapper.find('input[name="convenience_preference"]').exists()).toBe(true)
    expect(wrapper.findAll('fieldset')).toHaveLength(2)
    expect(wrapper.findAll('legend').map((legend) => legend.text())).toEqual([
      '你的基本信息',
      '口感与食用偏好',
    ])
    expect(wrapper.find('.choice-field--wide').text()).toContain('尝鲜偏好')
    expect(wrapper.find('.choice-field--wide').element.closest('fieldset').querySelector('legend').textContent)
      .toBe('你的基本信息')
    expect(wrapper.find('.horizon-field').element.closest('fieldset').querySelector('legend').textContent)
      .toBe('口感与食用偏好')
    expect(wrapper.text()).not.toContain('通常多久吃完购买的水果？')
  })

  it('uses the three price levels and preserves both default values', () => {
    const wrapper = mount(ProfileFields, {
      props: { modelValue: createDefaultProfile() },
    })

    expect(wrapper.findAll('select[name="price_level"] option').map((option) => option.element.value))
      .toEqual(['1', '2', '3'])
    expect(wrapper.find('.choice-field--wide').findAll('button').map((button) => button.attributes('aria-checked')))
      .toEqual(['false', 'true', 'false'])
    expect(wrapper.find('.horizon-field').findAll('button').map((button) => button.attributes('aria-checked')))
      .toEqual(['false', 'true', 'false'])
  })

  it('switches discovery and horizon values without adding duplicate controls', async () => {
    const model = createDefaultProfile()
    const wrapper = mount(ProfileFields, {
      props: { modelValue: model },
    })

    await wrapper.find('.choice-field--wide').findAll('button')[2].trigger('click')
    await wrapper.find('.horizon-field').findAll('button')[0].trigger('click')

    expect(model.discovery_level).toBe(2)
    expect(model.consumption_horizon_days).toBe(2)
    expect(wrapper.findAll('[name="discovery_level"]')).toHaveLength(0)
    expect(wrapper.findAll('[name="consumption_horizon_days"]')).toHaveLength(0)

    const names = wrapper.findAll('[name]').map((element) => element.attributes('name'))
    expect(new Set(names).size).toBe(names.length)
  })
})
