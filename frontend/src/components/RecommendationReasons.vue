<script setup>
defineProps({
  reasons: {
    type: Array,
    required: true,
  },
})
</script>

<template>
  <div class="reason-block">
    <h3>为什么推荐</h3>
    <ul>
      <li v-for="reason in reasons" :key="`${reason.code}-${reason.component}`">
        <span aria-hidden="true">✓</span>
        {{ reason.message }}
      </li>
    </ul>
  </div>
</template>
