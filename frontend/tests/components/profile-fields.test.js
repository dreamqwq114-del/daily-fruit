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
    expect(wrapper.find('input[name="texture_preference"]').exists()).toBe(true)
    expect(wrapper.find('input[name="texture_preference"]').attributes('aria-valuetext'))
      .toBe('未设置')
    expect(wrapper.findAll('.range-anchor-grid')).toHaveLength(3)
    expect(wrapper.findAll('.range-anchor')).toHaveLength(15)
    expect(wrapper.find('.range-anchor-grid').text()).toContain('0%')
    expect(wrapper.find('.range-anchor-grid').text()).toContain('100%')
    expect(wrapper.find('input[name="convenience_preference"]').exists()).toBe(true)
    expect(wrapper.findAll('fieldset')).toHaveLength(2)
    expect(wrapper.findAll('legend').map((legend) => legend.text())).toEqual([
      '你的基本信息',
      '口感与食用偏好',
    ])
    expect(wrapper.find('select[name="discovery_level"]').exists()).toBe(true)
    expect(wrapper.find('[role="radiogroup"][aria-label="尝鲜偏好"]').exists()).toBe(false)
    expect(wrapper.findAll('.basic-card')).toHaveLength(6)
    expect(wrapper.find('.basic-card--checkbox').text()).toContain('愿意通过网购购买水果')
    expect(wrapper.find('select[name="discovery_level"]').element.closest('fieldset').querySelector('legend').textContent)
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
    expect(wrapper.findAll('select[name="discovery_level"] option').map((option) => option.element.value))
      .toEqual(['0', '1', '2'])
    expect(wrapper.find('select[name="discovery_level"]').element.value).toBe('1')
    expect(wrapper.findAll('select[name="market_access_level"] option').map((option) => option.element.value))
      .toEqual(['1', '2', '3'])
    expect(wrapper.find('select[name="market_access_level"]').element.value).toBe('2')
    expect(wrapper.find('input[name="accepts_online_purchase"]').element.checked).toBe(false)
    const horizonSlider = wrapper.find('input[name="consumption_horizon_days"]')
    expect(horizonSlider.attributes('type')).toBe('range')
    expect(horizonSlider.attributes('min')).toBe('0')
    expect(horizonSlider.attributes('max')).toBe('2')
    expect(horizonSlider.attributes('step')).toBe('1')
    expect(horizonSlider.element.value).toBe('1')
  })

  it('switches discovery and horizon values without adding duplicate controls', async () => {
    const model = createDefaultProfile()
    const wrapper = mount(ProfileFields, {
      props: { modelValue: model },
    })

    await wrapper.find('select[name="discovery_level"]').setValue('2')
    await wrapper.find('select[name="market_access_level"]').setValue('1')
    await wrapper.find('input[name="accepts_online_purchase"]').setValue(true)
    await wrapper.find('input[name="consumption_horizon_days"]').setValue('0')

    expect(model.discovery_level).toBe(2)
    expect(model.market_access_level).toBe(1)
    expect(model.accepts_online_purchase).toBe(true)
    expect(model.consumption_horizon_days).toBe(2)
    expect(wrapper.findAll('[name="discovery_level"]')).toHaveLength(1)
    expect(wrapper.findAll('[name="consumption_horizon_days"]')).toHaveLength(1)

    const names = wrapper.findAll('[name]').map((element) => element.attributes('name'))
    expect(new Set(names).size).toBe(names.length)
  })

  it('allows an explicitly set sensory preference to be cleared back to null', async () => {
    const model = { ...createDefaultProfile(), texture_preference: 0.8 }
    const wrapper = mount(ProfileFields, { props: { modelValue: model } })

    const clearButton = wrapper.find('button.range-clear')
    expect(clearButton.element.closest('label')).toBeNull()
    await clearButton.trigger('click')

    expect(model.texture_preference).toBeNull()
    expect(wrapper.find('button.range-clear').exists()).toBe(false)
    expect(wrapper.find('input[name="texture_preference"]').attributes('aria-valuetext'))
      .toBe('未设置')
  })

  it('announces an explicit sensory value instead of its visual fallback', async () => {
    const model = createDefaultProfile()
    const wrapper = mount(ProfileFields, { props: { modelValue: model } })
    const slider = wrapper.find('input[name="sweet_preference"]')

    expect(slider.element.value).toBe('0.5')
    expect(slider.attributes('aria-valuetext')).toBe('未设置')
    await slider.setValue('0.7')

    expect(model.sweet_preference).toBe(0.7)
    expect(slider.attributes('aria-valuetext')).toBe('70%')
  })
})
