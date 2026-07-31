<script setup>
const completedChecks = [
  'Vue 3 与 Vite 最小入口',
  'FastAPI /health',
  '安全环境变量模板',
  '阶段一架构与实施计划',
]
</script>

<template>
  <main class="page-shell">
    <section class="hero" aria-labelledby="page-title">
      <p class="eyebrow">阶段一 · 项目骨架</p>
      <h1 id="page-title">每日水果推荐</h1>
      <p class="summary">
        当前只提供可启动骨架。水果数据、推荐算法和正式页面将在数据库审计完成后分阶段实现。
      </p>

      <ul class="check-list">
        <li v-for="item in completedChecks" :key="item">{{ item }}</li>
      </ul>

      <p class="notice">
        本项目不会在浏览器中保存数据库密码或 Supabase 高权限密钥。
      </p>
    </section>
  </main>
</template>

