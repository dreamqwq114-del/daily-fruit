<script setup>
defineProps({
  message: {
    type: String,
    required: true,
  },
  retryLabel: {
    type: String,
    default: '重新加载',
  },
})

defineEmits(['retry'])
</script>

<template>
  <div class="state-card state-card--error" role="alert">
    <span class="state-symbol" aria-hidden="true">!</span>
    <div>
      <h2>暂时没有完成</h2>
      <p>{{ message }}</p>
      <button class="button button--secondary" type="button" @click="$emit('retry')">
        {{ retryLabel }}
      </button>
    </div>
  </div>
</template>
