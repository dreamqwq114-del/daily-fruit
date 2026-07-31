<script setup>
defineProps({
  message: {
    type: String,
    default: '正在准备内容…',
  },
})
</script>

<template>
  <div class="state-card state-card--loading" role="status" aria-live="polite">
    <span class="loading-orbit" aria-hidden="true"></span>
    <p>{{ message }}</p>
  </div>
</template>
