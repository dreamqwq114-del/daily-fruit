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
  }
}

export function profileFromUser(user) {
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
