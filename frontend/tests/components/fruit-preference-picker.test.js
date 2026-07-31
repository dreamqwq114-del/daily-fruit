import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import FruitPreferencePicker from '../../src/components/FruitPreferencePicker.vue'

const fruits = [
  { id: 1, name: '苹果', taste: '清脆甜' },
  { id: 2, name: '香蕉', taste: '香甜软' },
]

function mountPicker() {
  return mount(FruitPreferencePicker, {
    props: {
      fruits,
      modelValue: {
        favoriteIds: [],
        forbiddenIds: [],
        legacyPreferences: [],
      },
    },
  })
}

describe('FruitPreferencePicker', () => {
  it('uses explicit favorite and forbidden buttons instead of per-fruit selects', async () => {
    const wrapper = mountPicker()
    expect(wrapper.findAll('select')).toHaveLength(0)
    expect(wrapper.text()).toContain('特别喜欢')
    expect(wrapper.text()).toContain('特别不能接受')
  })

  it('keeps a fruit in only one selection group', async () => {
    const wrapper = mountPicker()
    const favoriteButtons = wrapper.findAll('.fruit-choice-button--favorite')
    const forbiddenButtons = wrapper.findAll('.fruit-choice-button--forbidden')

    await favoriteButtons[0].trigger('click')
    const favoriteEvent = wrapper.emitted('update:modelValue')
    const favoriteSelection = favoriteEvent[favoriteEvent.length - 1][0]
    expect(favoriteSelection.favoriteIds).toEqual([1])
    await wrapper.setProps({ modelValue: favoriteSelection })

    await forbiddenButtons[0].trigger('click')
    const events = wrapper.emitted('update:modelValue')
    const latest = events[events.length - 1][0]
    expect(latest.favoriteIds).toEqual([])
    expect(latest.forbiddenIds).toEqual([1])
  })

  it('filters the fruit library by name and taste', async () => {
    const wrapper = mountPicker()
    await wrapper.find('input[type="search"]').setValue('软')
    expect(wrapper.findAll('.fruit-choice-card')).toHaveLength(1)
    expect(wrapper.text()).toContain('香蕉')
    expect(wrapper.text()).not.toContain('苹果')
  })
})
