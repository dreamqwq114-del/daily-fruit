import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import FeedbackButtons from '../../src/components/FeedbackButtons.vue'

describe('FeedbackButtons', () => {
  it('emits one selected feedback type', async () => {
    const wrapper = mount(FeedbackButtons, {
      props: { feedback: [], submittingType: '' },
    })
    const buttons = wrapper.findAll('button')

    expect(buttons).toHaveLength(5)
    await buttons[1].trigger('click')
    expect(wrapper.emitted('submit')).toEqual([['liked']])
  })

  it('disables selected feedback and all actions while submitting', () => {
    const selected = mount(FeedbackButtons, {
      props: {
        feedback: [{ id: 1, feedback_type: 'liked' }],
        submittingType: '',
      },
    })
    expect(selected.findAll('button')[1].attributes('disabled')).toBeDefined()
    expect(selected.findAll('button')[1].classes()).toContain(
      'feedback-button--selected',
    )

    const pending = mount(FeedbackButtons, {
      props: { feedback: [], submittingType: 'eaten' },
    })
    expect(
      pending.findAll('button').every((button) => button.attributes('disabled') !== undefined),
    ).toBe(true)
  })
})
