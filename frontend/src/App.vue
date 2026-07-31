<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppNavigation from './components/AppNavigation.vue'

const route = useRoute()
const showNavigation = computed(() => route.meta.showNavigation !== false)
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
    </header>

    <main class="app-main">
      <RouterView />
    </main>

    <AppNavigation v-if="showNavigation" />
  </div>
</template>
