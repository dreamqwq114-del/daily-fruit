<script setup>
import { computed } from 'vue'

const model = defineModel({ type: Object, required: true })

const regions = [
  { value: '华东', label: '华东' },
  { value: '华南', label: '华南' },
  { value: '华北', label: '华北' },
  { value: '华中', label: '华中' },
  { value: '西南', label: '西南' },
  { value: '西北', label: '西北' },
  { value: '东北', label: '东北' },
  { value: 'UNKNOWN', label: '暂不确定' },
]

const priceOptions = [
  { value: 1, title: '节省优先', description: '更在意日常价格' },
  { value: 2, title: '适中均衡', description: '价格和选择都平衡' },
  { value: 3, title: '品质优先', description: '可以接受更高价格' },
]

const discoveryOptions = [
  { value: 0, title: '偏保守', description: '优先推荐常见水果' },
  { value: 1, title: '偶尔尝鲜', description: '可以偶尔加入一种新水果' },
  { value: 2, title: '喜欢尝鲜', description: '更愿意发现没吃过的水果' },
]

const horizonOptions = [
  { value: 2, title: '1～2 天', description: '买了很快吃完' },
  { value: 4, title: '3～5 天', description: '日常适中' },
  { value: 7, title: '一周左右', description: '希望选择相对耐放的水果' },
]

const horizonIndex = computed({
  get() {
    const index = horizonOptions.findIndex(
      (option) => option.value === Number(model.value.consumption_horizon_days),
    )
    return index === -1 ? 1 : index
  },
  set(index) {
    const option = horizonOptions[Number(index)]
    model.value.consumption_horizon_days = option?.value ?? 4
  },
})

const selectedHorizon = computed(() => horizonOptions[horizonIndex.value] ?? horizonOptions[1])

const preferenceFields = [
  { key: 'sweet_preference', label: '偏甜', low: '清淡', high: '喜欢甜味' },
  { key: 'sour_preference', label: '偏酸', low: '不太酸', high: '喜欢酸味' },
  { key: 'soft_preference', label: '偏软', low: '有嚼感', high: '柔软' },
  { key: 'crisp_preference', label: '偏脆', low: '不强调', high: '清脆' },
  {
    key: 'convenience_preference',
    label: '食用便利',
    low: '不介意处理',
    high: '越方便越好',
  },
]
</script>

<template>
  <fieldset class="form-section">
    <legend>你的基本信息</legend>
    <div class="field-grid field-grid--basic">
      <label class="form-field form-field--wide">
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
        <span>所在地区</span>
        <select v-model="model.region" name="region" required>
          <option v-for="region in regions" :key="region.value" :value="region.value">
            {{ region.label }}
          </option>
        </select>
      </label>
      <label class="form-field">
        <span>价格偏好</span>
        <select v-model.number="model.price_level" name="price_level" required>
          <option v-for="option in priceOptions" :key="option.value" :value="option.value">
            {{ option.title }}
          </option>
        </select>
      </label>
      <label class="form-field form-field--wide">
        <span>尝鲜偏好</span>
        <select v-model.number="model.discovery_level" name="discovery_level" required>
          <option v-for="option in discoveryOptions" :key="option.value" :value="option.value">
            {{ option.title }}
          </option>
        </select>
      </label>
    </div>
  </fieldset>

  <fieldset class="form-section">
    <legend>口感与食用偏好</legend>
    <p class="section-help">食用时间表示你的消费周期，不代表水果实际保鲜时间，暂不参与推荐排序。</p>
    <div class="preference-sliders">
      <label v-for="field in preferenceFields" :key="field.key" class="range-field">
        <span class="range-heading">
          <strong>{{ field.label }}</strong>
          <output>{{ Math.round(Number(model[field.key]) * 100) }}%</output>
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
      <div class="horizon-field range-field">
        <span class="range-heading">
          <strong>食用时间</strong>
          <output>{{ selectedHorizon.title }}</output>
        </span>
        <span class="horizon-field__help">通常多久吃完购买的水果</span>
        <input
          v-model.number="horizonIndex"
          name="consumption_horizon_days"
          type="range"
          min="0"
          max="2"
          step="1"
          aria-label="通常多久吃完购买的水果"
          :aria-valuetext="`${selectedHorizon.title}，${selectedHorizon.description}`"
        />
        <span class="range-hints"><small>1～2 天</small><small>一周左右</small></span>
        <small class="horizon-slider-description">{{ selectedHorizon.description }}</small>
      </div>
    </div>
  </fieldset>
</template>
