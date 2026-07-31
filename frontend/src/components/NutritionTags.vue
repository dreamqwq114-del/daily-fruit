<script setup>
import { computed } from 'vue'

const props = defineProps({
  nutrition: {
    type: Object,
    default: null,
  },
})

const nutritionFields = [
  { key: 'vitamin_c', label: '维生素 C' },
  { key: 'fiber', label: '膳食纤维' },
  { key: 'potassium', label: '钾' },
  { key: 'folate', label: '叶酸' },
  { key: 'carotenoids', label: '类胡萝卜素' },
  { key: 'energy', label: '能量特点' },
]

const tags = computed(() => {
  if (!props.nutrition) return []

  return nutritionFields
    .map((field) => ({
      ...field,
      value: Number(props.nutrition[field.key] ?? 0),
    }))
    .sort((left, right) => right.value - left.value)
    .slice(0, 3)
})
</script>

<template>
  <div v-if="tags.length" class="nutrition-tags" aria-label="主要营养演示特点">
    <span v-for="tag in tags" :key="tag.key">
      {{ tag.label }}
      <small>{{ Math.round(tag.value * 100) }}</small>
    </span>
  </div>
  <p v-else class="muted-copy">暂无营养演示数据</p>
</template>
