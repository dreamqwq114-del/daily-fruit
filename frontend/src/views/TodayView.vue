<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '../api/http.js'
import {
  getTodayRecommendation,
  refreshRecommendation,
  submitFeedback,
} from '../api/recommendation.js'
import { getUser } from '../api/user.js'
import EmptyState from '../components/EmptyState.vue'
import ErrorState from '../components/ErrorState.vue'
import FruitCard from '../components/FruitCard.vue'
import LoadingState from '../components/LoadingState.vue'

const router = useRouter()
const user = ref(null)
const recommendation = ref(null)
const loading = ref(true)
const refreshing = ref(false)
const errorMessage = ref('')
const actionMessage = ref('')
const actionTone = ref('success')
const feedbackPending = ref({})

const recommendationItems = computed(() =>
  [...(recommendation.value?.items ?? [])].sort((left, right) => left.rank - right.rank),
)

const formattedDate = computed(() => {
  const dateValue = recommendation.value?.recommendation_date
  if (!dateValue) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(new Date(`${dateValue}T12:00:00`))
})

async function handleUserNotFound(error) {
  if (error instanceof ApiError && error.status === 404) {
    await router.replace('/onboarding')
    return true
  }
  return false
}

async function loadToday() {
  loading.value = true
  errorMessage.value = ''
  actionMessage.value = ''
  try {
    try {
      user.value = await getUser()
    } catch (error) {
      if (await handleUserNotFound(error)) return
      throw error
    }
    recommendation.value = await getTodayRecommendation()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

async function refreshToday() {
  if (refreshing.value) return

  refreshing.value = true
  actionMessage.value = ''
  actionTone.value = 'success'

  try {
    recommendation.value = await refreshRecommendation()
    actionMessage.value = '已经换成一组新的搭配。'
    actionTone.value = 'success'
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (error) {
    actionMessage.value = error.message
    actionTone.value = 'error'
  } finally {
    refreshing.value = false
  }
}

async function sendFeedback(item, feedbackType) {
  if (feedbackPending.value[item.id]) return

  feedbackPending.value = {
    ...feedbackPending.value,
    [item.id]: feedbackType,
  }
  actionMessage.value = ''
  actionTone.value = 'success'

  try {
    const result = await submitFeedback(item.id, feedbackType)
    const alreadyVisible = item.feedback.some(
      (entry) => entry.feedback_type === result.feedback_type,
    )
    if (!alreadyVisible) item.feedback.push(result)
    actionMessage.value = '反馈已记录，会用于调整后续推荐。'
    actionTone.value = 'success'
  } catch (error) {
    actionMessage.value = error.message
    actionTone.value = 'error'
  } finally {
    const nextPending = { ...feedbackPending.value }
    delete nextPending[item.id]
    feedbackPending.value = nextPending
  }
}

onMounted(loadToday)
</script>

<template>
  <section class="view-shell view-shell--today">
    <LoadingState v-if="loading" message="正在挑选今天的两种水果…" />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadToday" />
    <EmptyState
      v-else-if="!recommendation || recommendationItems.length !== 2"
      title="今天还没有可显示的推荐"
      message="请调整不能食用或不喜欢的水果后再试。"
    >
      <RouterLink class="button button--secondary" to="/preferences">调整偏好</RouterLink>
    </EmptyState>

    <template v-else>
      <header class="today-heading">
        <div>
          <p class="eyebrow">{{ formattedDate }} · {{ user.region }}</p>
          <h1>{{ user.username }}，今天吃这两种</h1>
          <p>结合 {{ user.region }} 的季节、你的口味与最近推荐记录。</p>
        </div>
        <span class="refresh-count">第 {{ recommendation.refresh_number + 1 }} 组</span>
      </header>

      <div class="recommendation-grid">
        <FruitCard
          v-for="item in recommendationItems"
          :key="item.id"
          :item="item"
          :submitting-feedback="feedbackPending[item.id] ?? ''"
          @feedback="sendFeedback(item, $event)"
        />
      </div>

      <p
        v-if="actionMessage"
        class="action-message"
        :class="{ 'action-message--error': actionTone === 'error' }"
        :role="actionTone === 'error' ? 'alert' : 'status'"
        aria-live="polite"
      >
        {{ actionMessage }}
      </p>

      <section class="refresh-panel" aria-labelledby="refresh-title">
        <div>
          <p class="eyebrow">想换个口味？</p>
          <h2 id="refresh-title">今天还可以看看另一组</h2>
          <p>换组会保留当前记录，并尽量避免立刻返回完全相同的搭配。</p>
        </div>
        <button class="button button--primary" type="button" :disabled="refreshing" @click="refreshToday">
          {{ refreshing ? '正在换一组…' : '换一组' }}
        </button>
      </section>
    </template>
  </section>
</template>
