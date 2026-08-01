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

export function createDefaultProfile() {
  // 与 UserBase 默认值保持一致：discovery=1、horizon=4、market=2。
  return {
    username: '',
    region: 'UNKNOWN',
    sweet_preference: 0.5,
    sour_preference: 0.5,
    soft_preference: 0.5,
    crisp_preference: 0.5,
    price_level: 2,
    convenience_preference: 0.5,
    discovery_level: 1,
    consumption_horizon_days: 4,
    market_access_level: 2,
    accepts_online_purchase: false,
  }
}

export function profileFromUser(user) {
  // 把后端回显合并到默认 profile，兼容旧用户缺少新字段的情况。
  const profile = createDefaultProfile()

  for (const key of Object.keys(profile)) {
    if (user?.[key] !== undefined && user[key] !== null) profile[key] = user[key]
  }

  // Existing V1 profiles used “全国” as a UI fallback. It is now represented
  // explicitly as UNKNOWN without changing the historical city column.
  if (!REGION_VALUES.has(profile.region) || profile.region === '全国') {
    profile.region = 'UNKNOWN'
  }
  return profile
}
