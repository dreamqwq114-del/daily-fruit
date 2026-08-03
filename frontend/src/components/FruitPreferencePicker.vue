<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import {
  displayOptionName,
  optionPreferenceSummary,
  optionQuickChoices,
  optionRowsForFruit,
  selectionOptionHint,
} from '../utils/selection-option-ui.js'

const props = defineProps({
  fruits: {
    type: Array,
    required: true,
  },
  optionPreferences: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:optionPreferences'])

const preferenceSelection = defineModel({ type: Object, required: true })
const pickerOpen = ref(false)
const activeGroup = ref('favoriteIds')
const searchTerm = ref('')
const pickerMessage = ref('')
const draftSelection = ref(null)
const optionPanelFruit = ref(null)
const optionPanelDraft = ref([])
const optionPanelMode = ref('quick')

const optionFruits = computed(() =>
  props.fruits.filter((fruit) =>
    Array.isArray(fruit.selection_options) && fruit.selection_options.some((option) => option.is_active),
  ),
)

const groups = [
  {
    key: 'favoriteIds',
    title: '特别喜欢',
    description: '会优先考虑这些水果',
    empty: '还没有标记，可以跳过。',
    chipClass: 'fruit-selection-group--favorite',
  },
  {
    key: 'dislikeIds',
    title: '不喜欢',
    description: '会明显降低推荐分数',
    empty: '没有特别不喜欢的水果。',
    chipClass: 'fruit-selection-group--dislike',
  },
  {
    key: 'forbiddenIds',
    title: '绝对不吃',
    description: '会完全排除，不会推荐',
    empty: '没有绝对不能接受的水果。',
    chipClass: 'fruit-selection-group--forbidden',
  },
]

const activeGroupInfo = computed(() =>
  groups.find((group) => group.key === activeGroup.value) ?? groups[0],
)

const filteredFruits = computed(() => {
  const keyword = searchTerm.value.trim().toLowerCase()
  if (!keyword) return props.fruits
  return props.fruits.filter((fruit) =>
    `${fruit.name} ${fruit.taste ?? ''}`.toLowerCase().includes(keyword),
  )
})

function ids(selection, key) {
  return selection?.[key] ?? []
}

function fruitsFor(group) {
  const selected = new Set(ids(preferenceSelection.value, group.key))
  return props.fruits.filter((fruit) => selected.has(fruit.id))
}

function openPicker(groupKey) {
  closeOptionPanel()
  activeGroup.value = groupKey
  searchTerm.value = ''
  pickerMessage.value = ''
  draftSelection.value = {
    favoriteIds: [...ids(preferenceSelection.value, 'favoriteIds')],
    dislikeIds: [...ids(preferenceSelection.value, 'dislikeIds')],
    forbiddenIds: [...ids(preferenceSelection.value, 'forbiddenIds')],
  }
  pickerOpen.value = true
}

function closePicker() {
  closeOptionPanel()
  pickerOpen.value = false
  draftSelection.value = null
  pickerMessage.value = ''
}

watch(pickerOpen, (isOpen) => {
  if (typeof document === 'undefined') return
  document.body.classList.toggle('fruit-picker-is-open', isOpen)
})

onBeforeUnmount(() => {
  if (typeof document !== 'undefined') {
    document.body.classList.remove('fruit-picker-is-open')
  }
})

function confirmPicker() {
  preferenceSelection.value = {
    favoriteIds: [...draftSelection.value.favoriteIds].sort((a, b) => a - b),
    dislikeIds: [...draftSelection.value.dislikeIds].sort((a, b) => a - b),
    forbiddenIds: [...draftSelection.value.forbiddenIds].sort((a, b) => a - b),
  }
  closePicker()
}

function confirmConflict(fruit, nextGroup, previousGroups) {
  const previous = previousGroups.map((group) => group.title).join('、')
  if (typeof window === 'undefined' || typeof window.confirm !== 'function') return true
  return window.confirm(`${fruit.name}已标记为“${previous}”。切换为“${nextGroup.title}”会清除原状态，是否继续？`)
}

function toggleDraft(fruit) {
  const groupKey = activeGroup.value
  const targetIds = new Set(ids(draftSelection.value, groupKey))
  if (targetIds.has(fruit.id)) {
    targetIds.delete(fruit.id)
    draftSelection.value = { ...draftSelection.value, [groupKey]: [...targetIds] }
    pickerMessage.value = ''
    return
  }

  if (groupKey === 'favoriteIds' && targetIds.size >= 5) {
    pickerMessage.value = '特别喜欢最多选择 5 种水果。可以先移除一个再添加。'
    return
  }

  const previousGroups = groups.filter(
    (group) => group.key !== groupKey && ids(draftSelection.value, group.key).includes(fruit.id),
  )
  if (previousGroups.length && !confirmConflict(fruit, activeGroupInfo.value, previousGroups)) return

  const next = { ...draftSelection.value }
  for (const group of groups) {
    next[group.key] = (group.key === groupKey
      ? [...ids(next, group.key), fruit.id]
      : ids(next, group.key).filter((id) => id !== fruit.id))
  }
  draftSelection.value = next
  pickerMessage.value = ''
}

function isDraftSelected(fruitId) {
  return ids(draftSelection.value, activeGroup.value).includes(fruitId)
}

function removeCommitted(groupKey, fruitId) {
  preferenceSelection.value = {
    ...preferenceSelection.value,
    [groupKey]: ids(preferenceSelection.value, groupKey).filter((id) => id !== fruitId),
  }
}

function optionPreference(fruitId, optionId) {
  return props.optionPreferences.find(
    (item) => Number(item.fruit_id) === fruitId && Number(item.option_id) === optionId,
  )?.preference ?? null
}

function activeOptions(fruit) {
  return fruit.selection_options?.filter((option) => option.is_active) ?? []
}

function optionSummary(fruit) {
  return optionPreferenceSummary(fruit, props.optionPreferences)
}

function optionChoices(fruit) {
  return optionQuickChoices(fruit, props.optionPreferences)
}

function optionHint(fruit) {
  return selectionOptionHint(fruit)
}

function fruitStatus(fruitId) {
  if (ids(draftSelection.value, 'favoriteIds').includes(fruitId)) return '喜欢'
  if (ids(draftSelection.value, 'dislikeIds').includes(fruitId)) return '不喜欢'
  if (ids(draftSelection.value, 'forbiddenIds').includes(fruitId)) return '绝对不吃'
  return '未设置'
}

function isQuickChoiceActive(choice) {
  if (optionPanelMode.value !== 'quick') return false
  if (choice.key === 'auto') return optionPanelDraft.value.length === 0
  if (choice.optionId === null || choice.optionId === 'custom') return false
  return optionPanelDraft.value.length === 1 &&
    Number(optionPanelDraft.value[0].option_id) === Number(choice.optionId) &&
    optionPanelDraft.value[0].preference === 'liked'
}

function isOptionPanelOpen(fruitId) {
  return Number(optionPanelFruit.value?.id) === Number(fruitId)
}

function openOptionPanel(fruit) {
  optionPanelFruit.value = fruit
  optionPanelDraft.value = optionRowsForFruit(fruit, props.optionPreferences).map((item) => ({ ...item }))
  optionPanelMode.value = 'quick'
}

function closeOptionPanel() {
  optionPanelFruit.value = null
  optionPanelDraft.value = []
  optionPanelMode.value = 'quick'
}

function setQuickOption(fruit, choice) {
  if (choice.optionId === 'custom') {
    optionPanelMode.value = 'custom'
    return
  }
  optionPanelMode.value = 'quick'
  optionPanelDraft.value = choice.optionId === null
    ? []
    : [{ fruit_id: fruit.id, option_id: choice.optionId, preference: 'liked' }]
}

function setCustomOption(fruit, option, preference) {
  const next = optionPanelDraft.value.filter(
    (item) => !(Number(item.fruit_id) === Number(fruit.id) && Number(item.option_id) === Number(option.id)),
  )
  if (preference) next.push({ fruit_id: fruit.id, option_id: option.id, preference })
  optionPanelDraft.value = next
}

function confirmOptionPanel() {
  if (!optionPanelFruit.value) return
  const fruitId = Number(optionPanelFruit.value.id)
  const others = props.optionPreferences.filter((item) => Number(item.fruit_id) !== fruitId)
  const next = [...others, ...optionPanelDraft.value]
    .sort((left, right) => Number(left.fruit_id) - Number(right.fruit_id) || Number(left.option_id) - Number(right.option_id))
  emit('update:optionPreferences', next)
  closeOptionPanel()
}
</script>

<template>
  <fieldset class="form-section fruit-preference-section">
    <legend>水果偏好</legend>
    <p class="section-help">
      只标记明确的强偏好。没有选择的水果表示你还没有提供明确意见，系统会从水果库中自动筛选。
    </p>

    <div class="fruit-selection-summary">
      <section
        v-for="group in groups"
        :key="group.key"
        class="fruit-selection-group"
        :class="group.chipClass"
      >
        <div class="fruit-selection-heading">
          <div>
            <h2>{{ group.title }} <span>{{ fruitsFor(group).length }}</span></h2>
            <small>{{ group.description }}</small>
          </div>
          <button class="button button--small" type="button" @click="openPicker(group.key)">
            + 添加水果
          </button>
        </div>
        <div v-if="fruitsFor(group).length" class="fruit-selection-chips">
          <button
            v-for="fruit in fruitsFor(group)"
            :key="`${group.key}-${fruit.id}`"
            class="fruit-selection-chip"
            type="button"
            :aria-label="`取消${group.title}${fruit.name}`"
            @click="removeCommitted(group.key, fruit.id)"
          >
            {{ fruit.name }} <span aria-hidden="true">×</span>
          </button>
        </div>
        <p v-else class="fruit-selection-empty">{{ group.empty }}</p>
      </section>
    </div>

    <p class="section-help fruit-preference-note">特别喜欢最多 5 种；“不喜欢”和“绝对不吃”会分开保存。</p>

    <div v-if="pickerOpen" class="fruit-picker-backdrop" @click.self="closePicker">
      <section class="fruit-picker-dialog" role="dialog" aria-modal="true" aria-labelledby="fruit-picker-title">
        <header class="fruit-picker-header">
          <div>
            <p class="eyebrow">从 24 种水果中选择</p>
            <h2 id="fruit-picker-title">{{ activeGroupInfo.title }}</h2>
            <p>{{ activeGroupInfo.description }}</p>
          </div>
          <button class="icon-button" type="button" aria-label="关闭选择器" @click="closePicker">×</button>
        </header>

        <label class="fruit-search-field">
          <span>搜索水果</span>
          <input v-model="searchTerm" type="search" placeholder="例如：苹果、甜、脆" autofocus />
        </label>

        <div class="fruit-picker-scroll-area">
          <p v-if="pickerMessage" class="inline-message" role="alert">{{ pickerMessage }}</p>
          <div class="fruit-picker-grid" aria-live="polite">
            <article
              v-for="fruit in filteredFruits"
              :key="fruit.id"
              class="fruit-picker-option"
              :class="{ 'is-selected': isDraftSelected(fruit.id) }"
            >
              <button
                class="fruit-picker-option-main"
                type="button"
                :aria-pressed="isDraftSelected(fruit.id)"
                @click="toggleDraft(fruit)"
              >
                <span class="fruit-initial" aria-hidden="true">{{ fruit.name.slice(0, 1) }}</span>
                <span><strong>{{ fruit.name }}</strong><small>{{ fruit.taste }}</small></span>
                <span class="fruit-picker-option-state">{{ isDraftSelected(fruit.id) ? '已选择' : '选择' }}</span>
              </button>
              <div v-if="optionFruits.some((item) => Number(item.id) === Number(fruit.id))" class="fruit-option-summary">
                <div>
                  <strong class="fruit-option-parent-status" :class="`is-${fruitStatus(fruit.id) === '喜欢' ? 'favorite' : fruitStatus(fruit.id) === '不喜欢' ? 'dislike' : fruitStatus(fruit.id) === '绝对不吃' ? 'forbidden' : 'unset'}`">{{ fruitStatus(fruit.id) }}</strong>
                  <span :class="{ 'is-muted': optionSummary(fruit) === '根据口感偏好自动匹配' }">类型偏好：{{ optionSummary(fruit) }}</span>
                </div>
                <button
                  class="fruit-option-edit"
                  type="button"
                  :aria-expanded="isOptionPanelOpen(fruit.id)"
                  :aria-label="`修改${fruit.name}类型偏好`"
                  @click.stop="openOptionPanel(fruit)"
                >修改 <span aria-hidden="true">›</span></button>
              </div>
              <div v-if="isOptionPanelOpen(fruit.id)" class="fruit-option-panel" role="dialog" :aria-label="`${fruit.name}类型偏好`">
                <h3>{{ fruit.name }}类型偏好</h3>
                <p v-if="optionHint(fruit)" class="section-help">{{ optionHint(fruit) }}</p>
                <div class="fruit-option-quick-list" role="radiogroup" :aria-label="`${fruit.name}快捷类型偏好`">
                  <button
                    v-for="choice in optionChoices(fruit)"
                    :key="choice.key"
                    type="button"
                    class="fruit-option-quick-choice"
                    :class="{ 'is-active': (choice.key === 'custom' && optionPanelMode === 'custom') || isQuickChoiceActive(choice) }"
                    role="radio"
                    :aria-checked="(choice.key === 'custom' && optionPanelMode === 'custom') || isQuickChoiceActive(choice)"
                    @click="setQuickOption(fruit, choice)"
                  >
                    <span aria-hidden="true">{{ (choice.key === 'custom' && optionPanelMode === 'custom') || isQuickChoiceActive(choice) ? '●' : '○' }}</span>
                    {{ choice.label }}
                  </button>
                </div>
                <div v-if="optionPanelMode === 'custom'" class="fruit-option-custom-list" role="group" :aria-label="`${fruit.name}详细类型偏好`">
                  <div v-for="option in activeOptions(fruit)" :key="option.id" class="fruit-option-custom-row">
                    <strong>{{ displayOptionName(option) }}</strong>
                    <div class="fruit-option-actions">
                      <button type="button" class="fruit-option-choice" :class="{ 'is-liked': optionPreference(fruit.id, option.id) === 'liked' || optionPanelDraft.find((item) => Number(item.option_id) === Number(option.id))?.preference === 'liked' }" @click="setCustomOption(fruit, option, 'liked')">喜欢</button>
                      <button type="button" class="fruit-option-choice" :class="{ 'is-disliked': optionPreference(fruit.id, option.id) === 'disliked' || optionPanelDraft.find((item) => Number(item.option_id) === Number(option.id))?.preference === 'disliked' }" @click="setCustomOption(fruit, option, 'disliked')">避开</button>
                      <button type="button" class="fruit-option-choice" @click="setCustomOption(fruit, option, null)">不确定</button>
                    </div>
                  </div>
                </div>
                <div class="fruit-option-panel-actions">
                  <button type="button" class="button button--ghost" @click.stop="closeOptionPanel">取消</button>
                  <button type="button" class="button button--primary" @click.stop="confirmOptionPanel">确认</button>
                </div>
              </div>
            </article>
          </div>
          <p v-if="!filteredFruits.length" class="fruit-selection-empty">没找到匹配的水果，可以换个关键词。</p>
        </div>

        <footer class="fruit-picker-actions">
          <button class="button button--ghost" type="button" @click="closePicker">取消</button>
          <button class="button button--primary" type="button" @click="confirmPicker">确认选择</button>
        </footer>
      </section>
    </div>
  </fieldset>
</template>
