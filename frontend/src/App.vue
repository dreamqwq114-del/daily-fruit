<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getSession, onAuthStateChange, signOut } from './auth/session.js'
import AppNavigation from './components/AppNavigation.vue'

const route = useRoute()
const router = useRouter()
const showNavigation = computed(() => route.meta.showNavigation !== false)
const authenticated = ref(false)
let unsubscribe = () => {}

async function logout() {
  await signOut()
  await router.replace('/login')
}

onMounted(async () => {
  authenticated.value = Boolean(await getSession())
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
      <button v-if="authenticated" class="button button--ghost" type="button" @click="logout">
        退出登录
      </button>
    </header>

    <main class="app-main">
      <RouterView />
    </main>

    <AppNavigation v-if="showNavigation" />
  </div>
</template>
