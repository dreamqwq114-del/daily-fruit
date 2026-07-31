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
  createDefaultFruitPreferenceSelection,
  preferencesToSelection,
  profileFromUser,
  selectionToPreferences,
} from '../utils/fruit-preferences.js'

const router = useRouter()
const route = useRoute()
const profile = reactive(createDefaultProfile())
const fruits = ref([])
const preferenceSelection = ref(createDefaultFruitPreferenceSelection())
const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref('')
const saveMessage = ref('')
const existingUser = ref(false)

async function loadPage() {
  loading.value = true
  errorMessage.value = ''

  try {
    fruits.value = await listFruits()

    let user
    try {
      user = await getUser()
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return
      throw error
    }

    existingUser.value = true
    Object.assign(profile, profileFromUser(user))

    const preferences = await getFruitPreferences()
    preferenceSelection.value = preferencesToSelection(preferences)
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
    let user
    if (existingUser.value) {
      user = await updateUser({ ...profile })
    } else {
      try {
        user = await createUser({ ...profile })
      } catch (error) {
        if (!(error instanceof ApiError && error.status === 409)) throw error
        existingUser.value = true
        user = await updateUser({ ...profile })
      }
    }

    existingUser.value = true

    try {
      await replaceFruitPreferences(selectionToPreferences(preferenceSelection.value))
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
      <RouterLink v-if="existingUser" class="text-link" to="/">返回今日推荐</RouterLink>
      <p class="eyebrow">每天两种 · 刚刚好</p>
      <h1>{{ existingUser ? '更新你的水果档案' : '先认识一下你的口味' }}</h1>
      <p>
        我们会结合地区、季节、价格、历史和反馈进行推荐。所有推荐理由都来自真实评分规则。
      </p>
    </header>

    <LoadingState v-if="loading" message="正在读取水果清单…" />
    <ErrorState v-else-if="errorMessage && !fruits.length" :message="errorMessage" @retry="loadPage" />

    <form v-else class="profile-form" @submit.prevent="saveOnboarding">
      <ProfileFields v-model="profile" />
      <FruitPreferencePicker v-model="preferenceSelection" :fruits="fruits" />

      <div v-if="saveMessage || errorMessage" class="inline-message" role="alert">
        <strong v-if="saveMessage">{{ saveMessage }}</strong>
        <span v-if="errorMessage">{{ errorMessage }}</span>
      </div>

      <div class="sticky-submit">
        <p>季节、价格和营养数据仅用于软件功能演示。</p>
        <button class="button button--primary" type="submit" :disabled="submitting">
          {{ submitting ? '正在保存…' : existingUser ? '保存修改' : '保存并查看今日推荐' }}
        </button>
      </div>
    </form>
  </div>
</template>
