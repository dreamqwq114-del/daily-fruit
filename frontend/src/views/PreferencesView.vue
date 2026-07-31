<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { listFruits } from '../api/fruit.js'
import { ApiError } from '../api/http.js'
import {
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
const profile = reactive(createDefaultProfile())
const fruits = ref([])
const preferenceSelection = ref(createDefaultFruitPreferenceSelection())
const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

async function handleUserNotFound(error) {
  if (error instanceof ApiError && error.status === 404) {
    await router.replace('/onboarding')
    return true
  }
  return false
}

async function loadPreferences() {
  loading.value = true
  errorMessage.value = ''
  try {
    let user
    try {
      user = await getUser()
    } catch (error) {
      if (await handleUserNotFound(error)) return
      throw error
    }
    const [fruitList, preferences] = await Promise.all([
      listFruits(),
      getFruitPreferences(),
    ])
    Object.assign(profile, profileFromUser(user))
    fruits.value = fruitList
    preferenceSelection.value = preferencesToSelection(preferences)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

async function savePreferences() {
  if (submitting.value) return

  submitting.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await updateUser({ ...profile })

    try {
      await replaceFruitPreferences(selectionToPreferences(preferenceSelection.value))
    } catch (error) {
      errorMessage.value = `基本信息已保存，但水果偏好保存失败：${error.message}`
      return
    }

    successMessage.value = '偏好已经保存，下一次生成推荐时会使用这些设置。'
  } catch (error) {
    if (!(await handleUserNotFound(error))) {
      errorMessage.value = error.message
    }
  } finally {
    submitting.value = false
  }
}

onMounted(loadPreferences)
</script>

<template>
  <section class="view-shell view-shell--wide">
    <header class="page-heading">
      <p class="eyebrow">你的选择</p>
      <h1>偏好设置</h1>
      <p>修改后不会改写历史推荐，会从下一次生成推荐时开始生效。</p>
    </header>

    <LoadingState v-if="loading" message="正在读取你的偏好…" />
    <ErrorState v-else-if="errorMessage && !fruits.length" :message="errorMessage" @retry="loadPreferences" />

    <form v-else class="profile-form" @submit.prevent="savePreferences">
      <ProfileFields v-model="profile" />
      <FruitPreferencePicker v-model="preferenceSelection" :fruits="fruits" />

      <p v-if="successMessage" class="inline-message inline-message--success" role="status">
        {{ successMessage }}
      </p>
      <p v-if="errorMessage" class="inline-message" role="alert">{{ errorMessage }}</p>

      <div class="sticky-submit sticky-submit--compact">
        <RouterLink class="button button--ghost" to="/">取消</RouterLink>
        <button class="button button--primary" type="submit" :disabled="submitting">
          {{ submitting ? '正在保存…' : '保存偏好' }}
        </button>
      </div>
    </form>
  </section>
</template>
