<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { getSession } from '../auth/session.js'

const router = useRouter()
const errorMessage = ref('')

onMounted(async () => {
  try {
    const session = await getSession()
    await router.replace(session ? '/' : '/login')
  } catch {
    errorMessage.value = '登录确认没有完成，请返回登录页重试。'
  }
})
</script>

<template>
  <section class="auth-page">
    <p v-if="errorMessage" role="alert">{{ errorMessage }}</p>
    <p v-else role="status">正在确认登录状态…</p>
    <RouterLink v-if="errorMessage" to="/login">返回登录</RouterLink>
  </section>
</template>
