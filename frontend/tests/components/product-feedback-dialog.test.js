import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const feedbackApi = vi.hoisted(() => ({
  createProductFeedback: vi.fn(),
}))

vi.mock('../../src/api/productFeedback.js', () => feedbackApi)

import ProductFeedbackDialog from '../../src/components/ProductFeedbackDialog.vue'

function mountDialog(props = {}) {
  return mount(ProductFeedbackDialog, {
    attachTo: document.body,
    props: { open: true, pageKey: 'today', ...props },
  })
}

describe('ProductFeedbackDialog', () => {
  beforeEach(() => {
    feedbackApi.createProductFeedback.mockReset()
    feedbackApi.createProductFeedback.mockResolvedValue({ id: 1 })
    document.body.style.overflow = ''
  })

  afterEach(() => {
    document.body.innerHTML = ''
    document.body.style.overflow = ''
  })

  it('validates empty content without sending a request', async () => {
    const wrapper = mountDialog()
    await wrapper.find('form').trigger('submit')

    expect(feedbackApi.createProductFeedback).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain('请填写 1 到 1000 字的反馈内容')
    wrapper.unmount()
  })

  it('submits the selected category, trimmed content and safe page key', async () => {
    const wrapper = mountDialog()
    await wrapper.find('input[value="bug"]').setValue(true)
    await wrapper.find('textarea').setValue('  点击按钮后报错。  ')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(feedbackApi.createProductFeedback).toHaveBeenCalledWith({
      category: 'bug',
      content: '点击按钮后报错。',
      page_key: 'today',
    })
    expect(document.body.textContent).toContain('感谢反馈，我们已经收到啦。')
    expect(wrapper.find('textarea').element.value).toBe('')
    wrapper.unmount()
  })

  it('sends null when the current route has no safe page key', async () => {
    const wrapper = mountDialog({ pageKey: null })
    await wrapper.find('textarea').setValue('鏈煡椤甸潰鐨勫缓璁€?')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(feedbackApi.createProductFeedback).toHaveBeenCalledWith({
      category: 'suggestion',
      content: '鏈煡椤甸潰鐨勫缓璁€?',
      page_key: null,
    })
    wrapper.unmount()
  })

  it('accepts content at the 1000 character boundary', async () => {
    const wrapper = mountDialog()
    const content = 'a'.repeat(1000)
    await wrapper.find('textarea').setValue(content)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(feedbackApi.createProductFeedback).toHaveBeenCalledWith({
      category: 'suggestion',
      content,
      page_key: 'today',
    })
    wrapper.unmount()
  })

  it('disables duplicate submissions and keeps a failed draft', async () => {
    let rejectRequest
    feedbackApi.createProductFeedback.mockReturnValue(
      new Promise((_resolve, reject) => {
        rejectRequest = reject
      }),
    )
    const wrapper = mountDialog()
    await wrapper.find('textarea').setValue('网络失败时应保留这段内容。')
    await wrapper.find('form').trigger('submit')
    await wrapper.find('form').trigger('submit')

    expect(feedbackApi.createProductFeedback).toHaveBeenCalledTimes(1)
    expect(wrapper.find('button[type="submit"]').element.disabled).toBe(true)

    rejectRequest(new Error('提交失败'))
    await flushPromises()
    expect(wrapper.find('textarea').element.value).toBe('网络失败时应保留这段内容。')
    expect(document.body.textContent).toContain('提交失败')
    wrapper.unmount()
  })

  it('keeps an unsubmitted draft after close and reopen', async () => {
    const wrapper = mountDialog()
    await wrapper.find('textarea').setValue('暂时不提交的建议。')
    await wrapper.setProps({ open: false })
    await wrapper.setProps({ open: true })

    expect(wrapper.find('textarea').element.value).toBe('暂时不提交的建议。')
    wrapper.unmount()
  })

  it('closes with Escape and restores body scrolling', async () => {
    const trigger = document.createElement('button')
    document.body.append(trigger)
    trigger.focus()
    const wrapper = mountDialog()
    await flushPromises()

    expect(document.body.style.overflow).toBe('hidden')
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(wrapper.emitted('close')).toHaveLength(1)
    await wrapper.setProps({ open: false })
    expect(document.body.style.overflow).toBe('')
    expect(document.activeElement).toBe(trigger)
    wrapper.unmount()
  })
})
