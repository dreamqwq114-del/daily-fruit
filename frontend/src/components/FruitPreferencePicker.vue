<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  fruits: {
    type: Array,
    required: true,
  },
})

const preferenceSelection = defineModel({ type: Object, required: true })
const searchTerm = ref('')

const filteredFruits = computed(() => {
  const keyword = searchTerm.value.trim().toLowerCase()
  if (!keyword) return props.fruits
  return props.fruits.filter((fruit) =>
    `${fruit.name} ${fruit.taste ?? ''}`.toLowerCase().includes(keyword),
  )
})

const favoriteFruits = computed(() =>
  props.fruits.filter((fruit) => preferenceSelection.value.favoriteIds.includes(fruit.id)),
)

const forbiddenFruits = computed(() =>
  props.fruits.filter((fruit) => preferenceSelection.value.forbiddenIds.includes(fruit.id)),
)

function isSelected(group, fruitId) {
  return preferenceSelection.value[group].includes(fruitId)
}

function toggleSelection(group, fruitId) {
  const otherGroup = group === 'favoriteIds' ? 'forbiddenIds' : 'favoriteIds'
  const currentIds = new Set(preferenceSelection.value[group])
  const otherIds = new Set(preferenceSelection.value[otherGroup])

  if (currentIds.has(fruitId)) {
    currentIds.delete(fruitId)
  } else {
    currentIds.add(fruitId)
    otherIds.delete(fruitId)
  }

  preferenceSelection.value = {
    ...preferenceSelection.value,
    [group]: [...currentIds].sort((left, right) => left - right),
    [otherGroup]: [...otherIds].sort((left, right) => left - right),
  }
}

function clearSelection(group) {
  preferenceSelection.value = {
    ...preferenceSelection.value,
    [group]: [],
  }
}
</script>

<template>
  <fieldset class="form-section fruit-preference-section">
    <legend>你有特别喜欢或不能接受的水果吗？</legend>
    <p class="section-help">
      只标记你的极端偏好。其余水果会由系统根据季节、价格、口感和营养互补自动选择。
    </p>

    <div class="fruit-selection-summary">
      <section class="fruit-selection-group fruit-selection-group--favorite" aria-labelledby="favorite-fruits-title">
        <div class="fruit-selection-heading">
          <h2 id="favorite-fruits-title">特别喜欢 <span>{{ favoriteFruits.length }}</span></h2>
          <button
            v-if="favoriteFruits.length"
            class="text-button"
            type="button"
            @click="clearSelection('favoriteIds')"
          >
            清空
          </button>
        </div>
        <div v-if="favoriteFruits.length" class="fruit-selection-chips">
          <button
            v-for="fruit in favoriteFruits"
            :key="`favorite-${fruit.id}`"
            class="fruit-selection-chip"
            type="button"
            :aria-label="`取消特别喜欢${fruit.name}`"
            @click="toggleSelection('favoriteIds', fruit.id)"
          >
            {{ fruit.name }}
            <span aria-hidden="true">×</span>
          </button>
        </div>
        <p v-else class="fruit-selection-empty">还没有标记，下方点击“特别喜欢”即可。</p>
      </section>

      <section class="fruit-selection-group fruit-selection-group--forbidden" aria-labelledby="forbidden-fruits-title">
        <div class="fruit-selection-heading">
          <h2 id="forbidden-fruits-title">特别不能接受 <span>{{ forbiddenFruits.length }}</span></h2>
          <button
            v-if="forbiddenFruits.length"
            class="text-button"
            type="button"
            @click="clearSelection('forbiddenIds')"
          >
            清空
          </button>
        </div>
        <div v-if="forbiddenFruits.length" class="fruit-selection-chips">
          <button
            v-for="fruit in forbiddenFruits"
            :key="`forbidden-${fruit.id}`"
            class="fruit-selection-chip"
            type="button"
            :aria-label="`取消特别不能接受${fruit.name}`"
            @click="toggleSelection('forbiddenIds', fruit.id)"
          >
            {{ fruit.name }}
            <span aria-hidden="true">×</span>
          </button>
        </div>
        <p v-else class="fruit-selection-empty">没有特别禁忌。为了保证有足够候选，建议不要一次排除太多水果。</p>
      </section>
    </div>

    <label class="fruit-search-field">
      <span>在水果库中搜索</span>
      <input v-model="searchTerm" type="search" placeholder="例如：苹果、甜、脆" />
    </label>

    <div class="fruit-choice-grid" aria-live="polite">
      <article v-for="fruit in filteredFruits" :key="fruit.id" class="fruit-choice-card">
        <span class="fruit-initial" aria-hidden="true">{{ fruit.name.slice(0, 1) }}</span>
        <span class="fruit-preference-name">
          <strong>{{ fruit.name }}</strong>
          <small>{{ fruit.taste }}</small>
        </span>
        <div class="fruit-choice-actions">
          <button
            class="fruit-choice-button fruit-choice-button--favorite"
            :class="{ 'is-selected': isSelected('favoriteIds', fruit.id) }"
            type="button"
            :aria-pressed="isSelected('favoriteIds', fruit.id)"
            @click="toggleSelection('favoriteIds', fruit.id)"
          >
            特别喜欢
          </button>
          <button
            class="fruit-choice-button fruit-choice-button--forbidden"
            :class="{ 'is-selected': isSelected('forbiddenIds', fruit.id) }"
            type="button"
            :aria-pressed="isSelected('forbiddenIds', fruit.id)"
            @click="toggleSelection('forbiddenIds', fruit.id)"
          >
            不能接受
          </button>
        </div>
      </article>
    </div>

    <p v-if="!filteredFruits.length" class="fruit-selection-empty">没找到匹配的水果，可以清空搜索后重试。</p>
  </fieldset>
</template>
