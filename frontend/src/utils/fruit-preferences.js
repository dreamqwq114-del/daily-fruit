// 前端 profile 的默认值和 API 数字枚举集中在这里，避免建档页与偏好页
// 各自维护一份状态。未选择的水果不会被序列化成 preference_score=0。
const REGION_VALUES = new Set([
  '华东',
  '华南',
  '华北',
  '华中',
  '西南',
  '西北',
  '东北',
  'UNKNOWN',
])

// 仅作可理解的语义锚点，不参与取值、算法、seed 或 API 合同。
export const SENSORY_ANCHORS = Object.freeze({
  sweet_preference: Object.freeze([
    Object.freeze({ name: '柠檬', percent: '0%' }),
    Object.freeze({ name: '绿心猕猴桃', percent: '25%' }),
    Object.freeze({ name: '草莓', percent: '50%' }),
    Object.freeze({ name: '苹果', percent: '75%' }),
    Object.freeze({ name: '荔枝', percent: '100%' }),
  ]),
  sour_preference: Object.freeze([
    Object.freeze({ name: '香蕉', percent: '0%' }),
    Object.freeze({ name: '苹果', percent: '25%' }),
    Object.freeze({ name: '草莓', percent: '50%' }),
    Object.freeze({ name: '绿心猕猴桃', percent: '75%' }),
    Object.freeze({ name: '柠檬', percent: '100%' }),
  ]),
  texture_preference: Object.freeze([
    Object.freeze({ name: '榴莲', percent: '0%' }),
    Object.freeze({ name: '软桃', percent: '25%' }),
    Object.freeze({ name: '火龙果', percent: '50%' }),
    Object.freeze({ name: '梨', percent: '75%' }),
    Object.freeze({ name: '清脆苹果', percent: '100%' }),
  ]),
})

const CLEARABLE_PREFERENCE_KEYS = new Set([
  'sweet_preference',
  'sour_preference',
  'texture_preference',
])

export function createDefaultFruitPreferenceSelection() {
  // 三类 ID 是展示状态；真正的数字 payload 在 selectionToPreferences 中生成。
  return {
    favoriteIds: [],
    dislikeIds: [],
    forbiddenIds: [],
  }
}

function sortedIds(values) {
  return [...new Set((values ?? []).map(Number))].sort((left, right) => left - right)
}

export function preferencesToSelection(preferences) {
  // 后端偏好行 → 页面三个集合；forbidden 优先于喜欢/不喜欢。
  const selection = createDefaultFruitPreferenceSelection()

  for (const preference of preferences ?? []) {
    const fruitId = Number(preference.fruit_id)
    const score = Number(preference.preference_score)

    if (preference.is_forbidden) {
      selection.forbiddenIds.push(fruitId)
    } else if (score === 2) {
      selection.favoriteIds.push(fruitId)
    } else if (score === -1) {
      selection.dislikeIds.push(fruitId)
    }
  }

  selection.favoriteIds = sortedIds(selection.favoriteIds)
  selection.dislikeIds = sortedIds(selection.dislikeIds)
  selection.forbiddenIds = sortedIds(selection.forbiddenIds)
  return selection
}

export function selectionToPreferences(selection) {
  // 页面集合 → PUT /api/me/fruit-preferences 的最小 payload。
  const preferences = new Map()

  for (const fruitId of selection.favoriteIds ?? []) {
    const id = Number(fruitId)
    preferences.set(id, {
      fruit_id: id,
      preference_score: 2,
      is_forbidden: false,
    })
  }

  for (const fruitId of selection.dislikeIds ?? []) {
    const id = Number(fruitId)
    preferences.set(id, {
      fruit_id: id,
      preference_score: -1,
      is_forbidden: false,
    })
  }

  for (const fruitId of selection.forbiddenIds ?? []) {
    const id = Number(fruitId)
    preferences.set(id, {
      fruit_id: id,
      preference_score: null,
      is_forbidden: true,
    })
  }

  return [...preferences.values()].sort(
    (left, right) => left.fruit_id - right.fruit_id,
  )
}

export function optionPreferencesToSelection(preferences) {
  return [...(preferences ?? [])]
    .filter(
      (item) =>
        item?.preference === 'liked' || item?.preference === 'disliked',
    )
    .map((item) => ({
      fruit_id: Number(item.fruit_id),
      option_id: Number(item.option_id),
      preference: item.preference,
    }))
    .sort(
      (left, right) =>
        left.fruit_id - right.fruit_id || left.option_id - right.option_id,
    )
}

export function selectionToOptionPreferences(preferences) {
  return optionPreferencesToSelection(preferences)
}

export function createDefaultProfile() {
  // 与 UserBase 默认值保持一致：discovery=1、horizon=4、market=2。
  return {
    username: '',
    region: 'UNKNOWN',
    sweet_preference: null,
    sour_preference: null,
    texture_preference: null,
    price_level: 2,
    convenience_preference: 0.5,
    discovery_level: 1,
    consumption_horizon_days: 4,
    market_access_level: 2,
    accepts_online_purchase: false,
    // UI-only dirty state; it is removed before building an API payload.
    __explicitlyChangedPreferences: new Set(),
  }
}

export function profileFromUser(user) {
  // 把后端回显合并到默认 profile，兼容旧用户缺少新字段的情况。
  const profile = createDefaultProfile()

  for (const key of Object.keys(profile)) {
    if (user?.[key] !== undefined) profile[key] = user[key]
  }

  // 仅在旧服务尚未提供 texture_preference 时读取兼容字段；冲突不填成
  // 0.5，避免前端把未知/矛盾状态伪装成中性偏好。
  if (user?.texture_preference === undefined && profile.texture_preference === null) {
    const soft = user?.soft_preference
    const crisp = user?.crisp_preference
    if (crisp !== null && crisp !== undefined && (soft === null || soft === undefined)) {
      profile.texture_preference = Number(crisp)
    } else if (soft !== null && soft !== undefined && (crisp === null || crisp === undefined)) {
      profile.texture_preference = 1 - Number(soft)
    } else if (soft !== null && soft !== undefined && crisp !== null && crisp !== undefined) {
      const converted = 1 - Number(soft)
      if (Math.abs(Number(crisp) - converted) <= 0.2) {
        profile.texture_preference = (Number(crisp) + converted) / 2
      }
    }
  }

  // Existing V1 profiles used “全国” as a UI fallback. It is now represented
  // explicitly as UNKNOWN without changing the historical city column.
  if (!REGION_VALUES.has(profile.region) || profile.region === '全国') {
    profile.region = 'UNKNOWN'
  }
  return profile
}

export function profileToApiPayload(profile) {
  const { __explicitlyChangedPreferences, ...payload } = profile
  const changed = __explicitlyChangedPreferences instanceof Set
    ? __explicitlyChangedPreferences
    : new Set()
  for (const key of CLEARABLE_PREFERENCE_KEYS) {
    if (!changed.has(key)) delete payload[key]
  }
  return payload
}
