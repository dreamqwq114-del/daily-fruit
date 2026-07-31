<script setup>
import { computed } from 'vue'

const props = defineProps({
  feedback: {
    type: Array,
    required: true,
  },
  submittingType: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['submit'])

const actions = [
  { type: 'eaten', label: '我吃了', symbol: '吃' },
  { type: 'liked', label: '喜欢', symbol: '赞' },
  { type: 'disliked', label: '不喜欢', symbol: '避' },
  { type: 'unavailable', label: '买不到', symbol: '缺' },
  { type: 'expensive', label: '太贵', symbol: '价' },
]

const submittedTypes = computed(
  () => new Set(props.feedback.map((entry) => entry.feedback_type)),
)
</script>

<template>
  <div class="feedback-block">
    <h3>这次推荐怎么样？</h3>
    <div class="feedback-actions">
      <button
        v-for="action in actions"
        :key="action.type"
        class="feedback-button"
        :class="{ 'feedback-button--selected': submittedTypes.has(action.type) }"
        type="button"
        :aria-pressed="submittedTypes.has(action.type)"
        :disabled="Boolean(submittingType) || submittedTypes.has(action.type)"
        @click="emit('submit', action.type)"
      >
        <span aria-hidden="true">{{ submittingType === action.type ? '…' : action.symbol }}</span>
        <small>{{ action.label }}</small>
      </button>
    </div>
  </div>
</template>
