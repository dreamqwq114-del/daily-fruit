<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import { createProductFeedback } from '../api/productFeedback.js'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  pageKey: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['close', 'submitted'])

const categories = [
  { value: 'recommendation_quality', label: '推荐结果问题' },
  { value: 'suggestion', label: '功能建议' },
  { value: 'bug', label: '页面或功能异常' },
  { value: 'fruit_content', label: '水果资料问题' },
  { value: 'other', label: '其他' },
]

const dialogRef = ref(null)
const closeButtonRef = ref(null)
const category = ref('suggestion')
const content = ref('')
const state = ref('idle')
const errorMessage = ref('')
let previousOverflow = ''
let lastFocusedElement = null

const isSubmitting = computed(() => state.value === 'submitting')
const isSuccess = computed(() => state.value === 'success')
const canSubmit = computed(
  () => !isSubmitting.value && !isSuccess.value && content.value.trim().length > 0,
)

function close() {
  if (isSubmitting.value) return
  emit('close')
}

function onBackdropClick(event) {
  if (event.target === event.currentTarget) close()
}

function getFocusableElements() {
  if (!dialogRef.value) return []
  return Array.from(
    dialogRef.value.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  )
}

function onKeydown(event) {
  if (!props.open) return
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
    return
  }
  if (event.key !== 'Tab') return

  const focusable = getFocusableElements()
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

async function focusDialog() {
  await nextTick()
  closeButtonRef.value?.focus()
}

function restorePageState() {
  document.body.style.overflow = previousOverflow
  if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
    lastFocusedElement.focus()
  }
  lastFocusedElement = null
}

async function submit() {
  if (isSubmitting.value || isSuccess.value) return

  const trimmedContent = content.value.trim()
  if (!trimmedContent || trimmedContent.length > 1000) {
    state.value = 'error'
    errorMessage.value = '请填写 1 到 1000 字的反馈内容。'
    return
  }

  state.value = 'submitting'
  errorMessage.value = ''
  try {
    await createProductFeedback({
      category: category.value,
      content: trimmedContent,
      page_key: props.pageKey,
    })
    category.value = 'suggestion'
    content.value = ''
    state.value = 'success'
    emit('submitted')
  } catch (error) {
    state.value = 'error'
    errorMessage.value = error?.message || '提交失败，请稍后重试。'
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      lastFocusedElement = document.activeElement
      previousOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      state.value = 'idle'
      errorMessage.value = ''
      document.addEventListener('keydown', onKeydown)
      await focusDialog()
    } else {
      document.removeEventListener('keydown', onKeydown)
      restorePageState()
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  restorePageState()
})
</script>

<template>
  <div
    v-if="props.open"
    class="product-feedback-backdrop"
    @mousedown="onBackdropClick"
  >
      <section
        ref="dialogRef"
        class="product-feedback-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="product-feedback-title"
        aria-describedby="product-feedback-description"
        @mousedown.stop
      >
        <header class="product-feedback-dialog__header">
          <div>
            <p class="eyebrow">每日水果</p>
            <h2 id="product-feedback-title">意见反馈</h2>
          </div>
          <button
            ref="closeButtonRef"
            class="product-feedback-dialog__close"
            type="button"
            aria-label="关闭反馈"
            @click="close"
          >
            ×
          </button>
        </header>

        <p id="product-feedback-description" class="product-feedback-dialog__description">
          你的建议会帮助每日水果变得更好。
        </p>

        <form class="product-feedback-form" @submit.prevent="submit">
          <fieldset>
            <legend>反馈类别</legend>
            <div class="product-feedback-categories">
              <label
                v-for="item in categories"
                :key="item.value"
                class="product-feedback-category"
                :class="{ 'product-feedback-category--selected': category === item.value }"
              >
                <input v-model="category" type="radio" name="product-feedback-category" :value="item.value" />
                <span>{{ item.label }}</span>
              </label>
            </div>
          </fieldset>

          <label class="product-feedback-form__label" for="product-feedback-content">
            反馈内容
          </label>
          <textarea
            id="product-feedback-content"
            v-model="content"
            name="content"
            maxlength="1000"
            rows="6"
            placeholder="请描述你遇到的问题或建议"
            aria-describedby="product-feedback-hint product-feedback-count"
          />
          <div class="product-feedback-form__meta">
            <span id="product-feedback-hint">支持换行，提交前会自动去除首尾空格。</span>
            <span id="product-feedback-count">{{ content.length }}/1000</span>
          </div>

          <p class="product-feedback-form__note">
            对当前水果的喜欢、不喜欢、太贵或买不到，请使用推荐卡片上的反馈；这里用于提交产品建议和问题。
          </p>

          <p v-if="errorMessage" class="inline-message" role="alert">{{ errorMessage }}</p>
          <p v-if="isSuccess" class="product-feedback-success" role="status">
            感谢反馈，我们已经收到啦。
          </p>

          <div class="product-feedback-form__actions">
            <button class="button button--ghost" type="button" :disabled="isSubmitting" @click="close">
              关闭
            </button>
            <button class="button button--primary" type="submit" :disabled="!canSubmit">
              {{ isSubmitting ? '提交中…' : '提交反馈' }}
            </button>
          </div>
        </form>
      </section>
  </div>
</template>
