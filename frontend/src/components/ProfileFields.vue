<script setup>
const model = defineModel({ type: Object, required: true })

const regions = ['全国', '华东', '华南', '华北', '华中', '西南', '西北', '东北']
const preferenceFields = [
  { key: 'sweet_preference', label: '偏甜', low: '清淡', high: '喜欢甜味' },
  { key: 'sour_preference', label: '偏酸', low: '不太酸', high: '喜欢酸味' },
  { key: 'soft_preference', label: '偏软', low: '有嚼感', high: '柔软' },
  { key: 'crisp_preference', label: '偏脆', low: '不强调', high: '清脆' },
  {
    key: 'convenience_preference',
    label: '食用便利',
    low: '可以处理',
    high: '越方便越好',
  },
]
</script>

<template>
  <fieldset class="form-section">
    <legend>你的基本信息</legend>
    <div class="field-grid field-grid--two">
      <label class="form-field">
        <span>怎么称呼你</span>
        <input
          v-model.trim="model.username"
          name="username"
          type="text"
          maxlength="80"
          autocomplete="nickname"
          placeholder="例如：小果"
          required
        />
      </label>
      <label class="form-field">
        <span>所在城市</span>
        <input
          v-model.trim="model.city"
          name="city"
          type="text"
          maxlength="100"
          autocomplete="address-level2"
          placeholder="例如：苏州"
          required
        />
      </label>
      <label class="form-field">
        <span>所在地区</span>
        <select v-model="model.region" name="region" required>
          <option v-for="region in regions" :key="region" :value="region">
            {{ region }}
          </option>
        </select>
      </label>
      <label class="form-field">
        <span>价格范围</span>
        <select v-model.number="model.price_level" name="price_level" required>
          <option :value="1">日常实惠</option>
          <option :value="2">适中均衡</option>
          <option :value="3">可以接受较高价格</option>
        </select>
      </label>
    </div>
  </fieldset>

  <fieldset class="form-section">
    <legend>口感偏好</legend>
    <div class="preference-sliders">
      <label v-for="field in preferenceFields" :key="field.key" class="range-field">
        <span class="range-heading">
          <strong>{{ field.label }}</strong>
          <output>{{ Math.round(model[field.key] * 100) }}%</output>
        </span>
        <input
          v-model.number="model[field.key]"
          :name="field.key"
          type="range"
          min="0"
          max="1"
          step="0.1"
        />
        <span class="range-hints"><small>{{ field.low }}</small><small>{{ field.high }}</small></span>
      </label>
    </div>
  </fieldset>
</template>
