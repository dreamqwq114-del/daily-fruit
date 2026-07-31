<script setup>
defineProps({
  title: {
    type: String,
    default: '这里还没有内容',
  },
  message: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <div class="state-card state-card--empty">
    <span class="state-symbol" aria-hidden="true">○</span>
    <div>
      <h2>{{ title }}</h2>
      <p>{{ message }}</p>
      <slot></slot>
    </div>
  </div>
</template>
