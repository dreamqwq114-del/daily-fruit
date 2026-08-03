import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import FruitPreferencePicker from '../../src/components/FruitPreferencePicker.vue'

const fruits = [
  { id: 1, name: '苹果', taste: '清脆甜' },
  { id: 2, name: '香蕉', taste: '香甜软' },
  { id: 3, name: '柠檬', taste: '明显酸味' },
]

function selection(overrides = {}) {
  return {
    favoriteIds: [],
    dislikeIds: [],
    forbiddenIds: [],
    ...overrides,
  }
}

function mountPicker(modelValue = selection(), fruitList = fruits) {
  return mount(FruitPreferencePicker, {
    props: { fruits: fruitList, modelValue },
  })
}

const optionFruits = [
  {
    id: 10,
    name: '桃',
    taste: '甜软',
    selection_options: [
      { id: 101, fruit_id: 10, code: 'crisp', name: '脆桃型', is_active: true },
      { id: 102, fruit_id: 10, code: 'soft', name: '软桃型', is_active: true },
    ],
  },
]

const peachAndKiwiOptionFruits = [
  {
    id: 10,
    name: 'peach',
    taste: 'sweet',
    selection_options: [
      { id: 101, fruit_id: 10, code: 'crisp', name: 'crisp peach', is_active: true },
      { id: 102, fruit_id: 10, code: 'soft', name: 'soft peach', is_active: true },
    ],
  },
  {
    id: 20,
    name: 'kiwifruit',
    taste: 'tart',
    selection_options: [
      { id: 201, fruit_id: 20, code: 'green', name: 'green heart', is_active: true },
      { id: 202, fruit_id: 20, code: 'yellow', name: 'yellow heart', is_active: true },
      { id: 203, fruit_id: 20, code: 'red', name: 'red heart', is_active: true },
    ],
  },
]

describe('FruitPreferencePicker', () => {
  it('does not render the old per-fruit select grid before opening the picker', () => {
    const wrapper = mountPicker()
    expect(wrapper.findAll('select')).toHaveLength(0)
    expect(wrapper.find('.fruit-picker-dialog').exists()).toBe(false)
    expect(wrapper.text()).toContain('特别喜欢')
    expect(wrapper.text()).toContain('不喜欢')
    expect(wrapper.text()).toContain('绝对不吃')
  })

  it('opens a searchable picker and confirms a favorite', async () => {
    const wrapper = mountPicker()
    await wrapper.findAll('.button--small')[0].trigger('click')
    expect(wrapper.find('.fruit-picker-dialog').exists()).toBe(true)
    expect(wrapper.find('.fruit-picker-scroll-area').exists()).toBe(true)

    await wrapper.find('.fruit-picker-option').trigger('click')
    expect(wrapper.find('.fruit-picker-option').classes()).toContain('is-selected')
    await wrapper.find('.fruit-picker-actions .button--primary').trigger('click')

    const latest = wrapper.emitted('update:modelValue').at(-1)[0]
    expect(latest.favoriteIds).toEqual([1])
    expect(latest.dislikeIds).toEqual([])
    expect(latest.forbiddenIds).toEqual([])
  })

  it('supports search and cancel without changing the committed selection', async () => {
    const wrapper = mountPicker()
    await wrapper.findAll('.button--small')[0].trigger('click')
    await wrapper.find('input[type="search"]').setValue('软')
    expect(wrapper.findAll('.fruit-picker-option')).toHaveLength(1)
    expect(wrapper.text()).toContain('香蕉')
    expect(wrapper.text()).not.toContain('苹果')

    await wrapper.find('.fruit-picker-option').trigger('click')
    await wrapper.find('.fruit-picker-actions .button--ghost').trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('keeps one status per fruit and asks before switching groups', async () => {
    const confirmSpy = vi.fn(() => true)
    window.confirm = confirmSpy
    const wrapper = mountPicker(selection({ favoriteIds: [1] }))
    await wrapper.findAll('.button--small')[2].trigger('click')
    await wrapper.find('.fruit-picker-option').trigger('click')
    await wrapper.find('.fruit-picker-actions .button--primary').trigger('click')

    const latest = wrapper.emitted('update:modelValue').at(-1)[0]
    expect(confirmSpy).toHaveBeenCalled()
    expect(latest.favoriteIds).toEqual([])
    expect(latest.forbiddenIds).toEqual([1])
    delete window.confirm
  })

  it('keeps selection options inside the parent fruit and supports clearing them', async () => {
    const wrapper = mount(FruitPreferencePicker, {
      props: {
        fruits: optionFruits,
        modelValue: selection(),
        optionPreferences: [
          { fruit_id: 10, option_id: 101, preference: 'liked' },
        ],
      },
    })

    await wrapper.find('.fruit-option-toggle').trigger('click')
    expect(wrapper.findAll('.fruit-option-row')).toHaveLength(2)
    expect(wrapper.findAll('.fruit-option-row')[0].findAll('.fruit-option-choice.is-selected')).toHaveLength(1)
    expect(wrapper.findAll('.fruit-option-row')[1].findAll('.fruit-option-choice.is-selected')).toHaveLength(1)

    await wrapper.findAll('.fruit-option-choice')[2].trigger('click')
    const latest = wrapper.emitted('update:optionPreferences').at(-1)[0]
    expect(latest).toEqual([])
  })

  it('renders both peach and kiwifruit options under their parent fruits', async () => {
    const wrapper = mount(FruitPreferencePicker, {
      props: {
        fruits: peachAndKiwiOptionFruits,
        modelValue: selection(),
      },
    })

    expect(wrapper.findAll('.fruit-option-card')).toHaveLength(2)
    expect(wrapper.text()).toContain('peach')
    expect(wrapper.text()).toContain('kiwifruit')

    const toggles = wrapper.findAll('.fruit-option-toggle')
    await toggles[0].trigger('click')
    expect(wrapper.findAll('.fruit-option-row')).toHaveLength(2)
    expect(wrapper.text()).toContain('crisp peach')
    expect(wrapper.text()).toContain('soft peach')

    await toggles[1].trigger('click')
    expect(wrapper.findAll('.fruit-option-row')).toHaveLength(5)
    expect(wrapper.text()).toContain('green heart')
    expect(wrapper.text()).toContain('yellow heart')
    expect(wrapper.text()).toContain('red heart')
  })

  it('enforces the five-fruit favorite limit in the picker', async () => {
    const sixFruits = [...fruits, { id: 4, name: '梨', taste: '清甜' }, { id: 5, name: '桃', taste: '柔软甜' }, { id: 6, name: '葡萄', taste: '甜多汁' }]
    const wrapper = mountPicker(selection({ favoriteIds: [1, 2, 3, 4, 5] }), sixFruits)
    await wrapper.findAll('.button--small')[0].trigger('click')
    await wrapper.findAll('.fruit-picker-option')[5].trigger('click')
    expect(wrapper.text()).toContain('特别喜欢最多选择 5 种')
  })
})
