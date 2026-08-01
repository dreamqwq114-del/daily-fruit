import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ProfileFields from '../../src/components/ProfileFields.vue'
import { createDefaultProfile } from '../../src/utils/fruit-preferences.js'

describe('ProfileFields', () => {
  it('does not render city and exposes the supported profile controls', () => {
    const wrapper = mount(ProfileFields, {
      props: { modelValue: createDefaultProfile() },
    })

    expect(wrapper.find('input[name="city"]').exists()).toBe(false)
    expect(wrapper.find('input[name="username"]').exists()).toBe(true)
    expect(wrapper.findAll('select[name="region"] option')).toHaveLength(8)
    expect(wrapper.findAll('input[type="range"]')).toHaveLength(5)
    expect(wrapper.find('input[name="convenience_preference"]').exists()).toBe(true)
    expect(wrapper.findAll('.choice-card-grid')).toHaveLength(2)
    expect(wrapper.findAll('.choice-card')).toHaveLength(6)
  })

  it('uses the three price levels and 2/4/7 horizon values', () => {
    const wrapper = mount(ProfileFields, {
      props: { modelValue: createDefaultProfile() },
    })

    expect(wrapper.findAll('select[name="price_level"] option').map((option) => option.element.value))
      .toEqual(['1', '2', '3'])
    expect(wrapper.findAll('.choice-card-grid')[0].findAll('button').map((button) => button.attributes('aria-pressed')))
      .toEqual(['false', 'true', 'false'])
  })
})
