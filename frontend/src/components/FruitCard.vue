<script setup>
import { ref } from 'vue'

import FeedbackButtons from './FeedbackButtons.vue'
import NutritionTags from './NutritionTags.vue'
import RecommendationReasons from './RecommendationReasons.vue'

defineProps({
  item: {
    type: Object,
    required: true,
  },
  submittingFeedback: {
    type: String,
    default: '',
  },
})

defineEmits(['feedback'])

const imageFailed = ref(false)

const rankLabels = {
  1: '今日首选',
  2: '营养搭档',
}
</script>

<template>
  <article class="fruit-card" :class="`fruit-card--rank-${item.rank}`">
    <div class="fruit-card__visual">
      <img
        v-if="item.fruit.image_url && !imageFailed"
        :src="item.fruit.image_url"
        :alt="item.fruit.name"
        @error="imageFailed = true"
      />
      <span v-else aria-hidden="true">{{ item.fruit.name.slice(0, 1) }}</span>
      <p>{{ rankLabels[item.rank] }}</p>
    </div>

    <div class="fruit-card__content">
      <header class="fruit-card__heading">
        <div>
          <p class="eyebrow">{{ item.fruit.display_group || item.fruit.category }} · {{ item.fruit.taste }}</p>
          <h2>{{ item.fruit.name }}</h2>
        </div>
        <span class="score-chip" :aria-label="`推荐匹配度 ${Math.round(item.score * 100)} 分`">
          {{ Math.round(item.score * 100) }}<small>分</small>
        </span>
      </header>

      <p v-if="item.pair_score != null" class="score-detail">
        本水果分 {{ Math.round((item.individual_score ?? item.score) * 100) }} · 组合分 {{ Math.round(item.pair_score * 100) }}
      </p>

      <p class="fruit-description">{{ item.fruit.description }}</p>

      <aside v-if="item.daily_fact" class="fruit-fact" aria-label="每日冷知识">
        <span class="fruit-fact__label">每日冷知识</span>
        <p>{{ item.daily_fact.fact_text }}</p>
      </aside>

      <div class="portion-row">
        <span aria-hidden="true">一</span>
        <p><small>建议份量</small><strong>{{ item.fruit.default_portion }}</strong></p>
        <p><small>价格等级</small><strong>{{ '¥'.repeat(item.fruit.average_price_level) }}</strong></p>
      </div>

      <NutritionTags :nutrition="item.fruit.nutrition" />
      <p class="nutrition-note">标签数值为 0–100 的归一化演示分数。</p>
      <RecommendationReasons :reasons="item.reasons" />
      <FeedbackButtons
        :feedback="item.feedback"
        :submitting-type="submittingFeedback"
        @submit="$emit('feedback', $event)"
      />
    </div>
  </article>
</template>
