<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '../api/http.js'
import { listRecommendationHistory } from '../api/recommendation.js'
import { getUser } from '../api/user.js'
import EmptyState from '../components/EmptyState.vue'
import ErrorState from '../components/ErrorState.vue'
import LoadingState from '../components/LoadingState.vue'
import RecommendationReasons from '../components/RecommendationReasons.vue'

const router = useRouter()
const user = ref(null)
const history = ref([])
const loading = ref(true)
const errorMessage = ref('')

const feedbackLabels = {
  eaten: '我吃了',
  liked: '喜欢',
  disliked: '不喜欢',
  unavailable: '买不到',
  expensive: '太贵',
  tired_of_it: '吃腻了',
  change_requested: '请求换组',
}

function formatDate(value) {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(`${value}T12:00:00`))
}

function sortedItems(items) {
  return [...items].sort((left, right) => left.rank - right.rank)
}

async function loadHistory() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [userResult, historyResult] = await Promise.all([
      getUser(),
      listRecommendationHistory(),
    ])
    user.value = userResult
    history.value = historyResult
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      await router.replace('/onboarding')
    } else {
      errorMessage.value = error.message
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadHistory)
</script>

<template>
  <section class="view-shell view-shell--wide">
    <header class="page-heading page-heading--split">
      <div>
        <p class="eyebrow">最近 30 组</p>
        <h1>推荐历史</h1>
        <p v-if="user">{{ user.username }} 的推荐、换组和反馈都在这里。</p>
      </div>
      <RouterLink class="button button--secondary" to="/">返回今日</RouterLink>
    </header>

    <LoadingState v-if="loading" message="正在整理推荐记录…" />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadHistory" />
    <EmptyState
      v-else-if="history.length === 0"
      title="还没有推荐历史"
      message="生成第一组今日推荐后，这里会显示水果、理由和你的反馈。"
    >
      <RouterLink class="button button--primary" to="/">查看今日推荐</RouterLink>
    </EmptyState>

    <div v-else class="history-list">
      <article v-for="entry in history" :key="entry.id" class="history-card">
        <header class="history-card__heading">
          <div>
            <p class="eyebrow">{{ formatDate(entry.recommendation_date) }}</p>
            <h2>第 {{ entry.refresh_number + 1 }} 组推荐</h2>
          </div>
          <span class="status-chip" :class="`status-chip--${entry.status}`">
            {{ entry.status === 'active' ? '当前推荐' : '已被替换' }}
          </span>
        </header>

        <div class="history-items">
          <section v-for="item in sortedItems(entry.items)" :key="item.id" class="history-item">
            <div class="history-fruit-heading">
              <span class="fruit-initial" aria-hidden="true">{{ item.fruit.name.slice(0, 1) }}</span>
              <div>
                <small>{{ item.rank === 1 ? '首选' : '搭档' }} · {{ item.fruit.category }}</small>
                <h3>{{ item.fruit.name }}</h3>
              </div>
            </div>

            <RecommendationReasons :reasons="item.reasons" />

            <div v-if="item.feedback.length" class="history-feedback" aria-label="已提交反馈">
              <span v-for="feedback in item.feedback" :key="feedback.id">
                {{ feedbackLabels[feedback.feedback_type] ?? feedback.feedback_type }}
              </span>
            </div>
          </section>
        </div>
      </article>
    </div>
  </section>
</template>
