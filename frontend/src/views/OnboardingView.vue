<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { listFruits } from '../api/fruit.js'
import { ApiError } from '../api/http.js'
import {
  createUser,
  getFruitPreferences,
  getUser,
  replaceFruitPreferences,
  updateUser,
} from '../api/user.js'
import ErrorState from '../components/ErrorState.vue'
import FruitPreferencePicker from '../components/FruitPreferencePicker.vue'
import LoadingState from '../components/LoadingState.vue'
import ProfileFields from '../components/ProfileFields.vue'
import {
  createDefaultProfile,
  preferencesToState,
  profileFromUser,
  stateToPreferences,
} from '../utils/fruit-preferences.js'
import { clearUserId, getUserId, setUserId } from '../utils/user-session.js'

const router = useRouter()
const route = useRoute()
const profile = reactive(createDefaultProfile())
const fruits = ref([])
const preferenceState = ref({})
const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref('')
const saveMessage = ref('')
const existingUserId = ref(getUserId())

function initializeFruitState() {
  preferenceState.value = Object.fromEntries(
    fruits.value.map((fruit) => [fruit.id, preferenceState.value[fruit.id] ?? 'neutral']),
  )
}

async function loadPage() {
  loading.value = true
  errorMessage.value = ''

  try {
    fruits.value = await listFruits()
    initializeFruitState()

    if (existingUserId.value) {
      try {
        const [user, preferences] = await Promise.all([
          getUser(existingUserId.value),
          getFruitPreferences(existingUserId.value),
        ])
        Object.assign(profile, profileFromUser(user))
        preferenceState.value = {
          ...preferenceState.value,
          ...preferencesToState(preferences),
        }
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          clearUserId()
          existingUserId.value = null
        } else {
          throw error
        }
      }
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

async function saveOnboarding() {
  if (submitting.value) return

  submitting.value = true
  errorMessage.value = ''
  saveMessage.value = ''

  try {
    const user = existingUserId.value
      ? await updateUser(existingUserId.value, { ...profile })
      : await createUser({ ...profile })

    if (!existingUserId.value) {
      existingUserId.value = user.id
      setUserId(user.id)
    }

    try {
      await replaceFruitPreferences(
        user.id,
        stateToPreferences(preferenceState.value),
      )
    } catch (error) {
      saveMessage.value = '基本信息已保存，但水果偏好暂未保存。请再次点击保存重试。'
      errorMessage.value = error.message
      return
    }

    const nextPath =
      typeof route.query.next === 'string' &&
      route.query.next.startsWith('/') &&
      !route.query.next.startsWith('/onboarding')
        ? route.query.next
        : '/'
    await router.replace(nextPath)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    submitting.value = false
  }
}

onMounted(loadPage)
</script>

<template>
  <div class="onboarding-page">
    <header class="onboarding-hero">
      <RouterLink v-if="existingUserId" class="text-link" to="/">返回今日推荐</RouterLink>
      <p class="eyebrow">每天两种 · 刚刚好</p>
      <h1>{{ existingUserId ? '更新你的水果档案' : '先认识一下你的口味' }}</h1>
      <p>
        我们会结合地区、季节、价格、历史和反馈进行推荐。所有推荐理由都来自真实评分规则。
      </p>
    </header>

    <LoadingState v-if="loading" message="正在读取水果清单…" />
    <ErrorState v-else-if="errorMessage && !fruits.length" :message="errorMessage" @retry="loadPage" />

    <form v-else class="profile-form" @submit.prevent="saveOnboarding">
      <ProfileFields v-model="profile" />
      <FruitPreferencePicker v-model="preferenceState" :fruits="fruits" />

      <div v-if="saveMessage || errorMessage" class="inline-message" role="alert">
        <strong v-if="saveMessage">{{ saveMessage }}</strong>
        <span v-if="errorMessage">{{ errorMessage }}</span>
      </div>

      <div class="sticky-submit">
        <p>季节、价格和营养数据仅用于软件功能演示。</p>
        <button class="button button--primary" type="submit" :disabled="submitting">
          {{ submitting ? '正在保存…' : existingUserId ? '保存修改' : '保存并查看今日推荐' }}
        </button>
      </div>
    </form>
  </div>
</template>
