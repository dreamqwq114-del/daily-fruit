<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { signInWithPassword, signUp } from '../auth/session.js'
import { isAuthConfigured } from '../auth/supabase.js'

const route = useRoute()
const router = useRouter()
const form = reactive({ email: '', password: '' })
const mode = ref('signin')
const submitting = ref(false)
const errorMessage = ref('')
const statusMessage = ref('')

async function submit() {
  if (submitting.value) return
  submitting.value = true
  errorMessage.value = ''
  statusMessage.value = ''

  try {
    if (mode.value === 'signup') {
      const { session } = await signUp(form.email.trim(), form.password)
      if (!session) {
        statusMessage.value = '注册成功，请打开邮箱确认后再登录。'
        mode.value = 'signin'
        return
      }
    } else {
      await signInWithPassword(form.email.trim(), form.password)
    }

    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/')
      ? route.query.next
      : '/'
    await router.replace(next)
  } catch (error) {
    errorMessage.value = error?.message || '登录没有成功，请稍后重试。'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="auth-page">
    <div class="auth-card">
      <p class="eyebrow">每日水果 · 安全登录</p>
      <h1>{{ mode === 'signin' ? '欢迎回来' : '创建账号' }}</h1>
      <p>登录信息由 Supabase Auth 管理，水果偏好仍只通过 FastAPI 访问。</p>

      <p v-if="!isAuthConfigured()" class="inline-message" role="alert">
        在线登录服务尚未配置。
      </p>

      <form class="auth-form" @submit.prevent="submit">
        <label>
          邮箱
          <input v-model="form.email" type="email" autocomplete="email" required />
        </label>
        <label>
          密码
          <input
            v-model="form.password"
            type="password"
            :autocomplete="mode === 'signin' ? 'current-password' : 'new-password'"
            minlength="8"
            required
          />
        </label>
        <p v-if="errorMessage" class="inline-message" role="alert">{{ errorMessage }}</p>
        <p v-if="statusMessage" class="inline-message inline-message--success" role="status">
          {{ statusMessage }}
        </p>
        <button class="button button--primary" type="submit" :disabled="submitting || !isAuthConfigured()">
          {{ submitting ? '请稍候…' : mode === 'signin' ? '登录' : '注册' }}
        </button>
      </form>

      <button class="auth-switch" type="button" @click="mode = mode === 'signin' ? 'signup' : 'signin'">
        {{ mode === 'signin' ? '还没有账号？立即注册' : '已经有账号？返回登录' }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.auth-page { min-height: 100vh; display: grid; place-items: center; padding: 24px; }
.auth-card { width: min(100%, 440px); padding: 28px; border-radius: 24px; background: var(--surface, #fff); box-shadow: 0 18px 60px rgba(48, 71, 45, .12); }
.auth-card h1 { margin: 8px 0; }
.auth-form { display: grid; gap: 16px; margin-top: 24px; }
.auth-form label { display: grid; gap: 8px; font-weight: 700; }
.auth-form input { min-width: 0; padding: 12px 14px; border: 1px solid #cad8c7; border-radius: 12px; font: inherit; }
.auth-switch { width: 100%; margin-top: 18px; border: 0; background: transparent; color: #39733d; cursor: pointer; }
</style>
