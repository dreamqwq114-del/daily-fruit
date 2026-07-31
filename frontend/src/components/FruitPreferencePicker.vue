<script setup>
import { FRUIT_PREFERENCE_OPTIONS } from '../utils/fruit-preferences.js'

defineProps({
  fruits: {
    type: Array,
    required: true,
  },
})

const preferenceState = defineModel({ type: Object, required: true })
</script>

<template>
  <fieldset class="form-section">
    <legend>水果选择</legend>
    <p class="section-help">
      标记喜欢、不喜欢或不能食用的水果。未选择的水果按“无所谓”处理。
    </p>
    <div class="fruit-preference-grid">
      <label v-for="fruit in fruits" :key="fruit.id" class="fruit-preference-row">
        <span class="fruit-initial" aria-hidden="true">{{ fruit.name.slice(0, 1) }}</span>
        <span class="fruit-preference-name">
          <strong>{{ fruit.name }}</strong>
          <small>{{ fruit.taste }}</small>
        </span>
        <select
          v-model="preferenceState[fruit.id]"
          :name="`fruit-${fruit.id}`"
          :aria-label="`${fruit.name}偏好`"
        >
          <option
            v-for="option in FRUIT_PREFERENCE_OPTIONS"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }}
          </option>
        </select>
      </label>
    </div>
  </fieldset>
</template>
