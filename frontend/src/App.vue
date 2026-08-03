<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getSession, onAuthStateChange, signOut } from './auth/session.js'
import AppNavigation from './components/AppNavigation.vue'
import ProductFeedbackDialog from './components/ProductFeedbackDialog.vue'

const route = useRoute()
const router = useRouter()
const showNavigation = computed(() => route.meta.showNavigation !== false)
const pageKeyByRouteName = {
  today: 'today',
  preferences: 'preferences',
  history: 'history',
}
const feedbackPageKey = computed(
  () => pageKeyByRouteName[route.name] ?? null,
)
const authenticated = ref(false)
const loggingOut = ref(false)
const logoutError = ref('')
const feedbackOpen = ref(false)
let unsubscribe = () => {}

const feedbackAvailable = computed(
  () => Boolean(
    authenticated.value && showNavigation.value && feedbackPageKey.value,
  ),
)

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  logoutError.value = ''
  try {
    await signOut()
    await router.replace('/login')
  } catch {
    logoutError.value = '退出失败，请检查网络后重试。'
  } finally {
    loggingOut.value = false
  }
}

function openFeedback() {
  if (feedbackAvailable.value) feedbackOpen.value = true
}

watch(feedbackAvailable, (available) => {
  if (!available) feedbackOpen.value = false
})

onMounted(async () => {
  try {
    authenticated.value = Boolean(await getSession())
  } catch {
    authenticated.value = false
  }
  unsubscribe = onAuthStateChange((_event, session) => {
    authenticated.value = Boolean(session)
  })
})
onBeforeUnmount(() => unsubscribe())
</script>

<template>
  <div class="app-shell">
    <header v-if="showNavigation" class="app-header">
      <RouterLink class="brand" to="/" aria-label="每日水果推荐首页">
        <span class="brand-mark" aria-hidden="true">果</span>
        <span>
          <strong>每日水果</strong>
          <small>今天吃什么，交给好选择</small>
        </span>
      </RouterLink>
      <div v-if="authenticated" class="header-actions">
        <button
          v-if="feedbackAvailable"
          class="button button--ghost feedback-trigger"
          type="button"
          @click="openFeedback"
        >
          反馈
        </button>
        <div class="logout-controls">
          <button
            class="button button--ghost"
            type="button"
            :disabled="loggingOut"
            @click="logout"
          >
            {{ loggingOut ? '正在退出…' : '退出登录' }}
          </button>
          <small v-if="logoutError" class="logout-error" role="alert">{{ logoutError }}</small>
        </div>
      </div>
    </header>

    <main class="app-main">
      <RouterView />
    </main>

    <AppNavigation v-if="showNavigation" />
    <ProductFeedbackDialog
      v-if="authenticated"
      :open="feedbackOpen"
      :page-key="feedbackPageKey"
      @close="feedbackOpen = false"
    />
  </div>
</template>
