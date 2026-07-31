export function createDefaultFruitPreferenceSelection() {
  return {
    favoriteIds: [],
    forbiddenIds: [],
    // Keep older like/dislike records until the new UI explicitly replaces them.
    legacyPreferences: [],
  }
}

export function preferencesToSelection(preferences) {
  const selection = createDefaultFruitPreferenceSelection()

  for (const preference of preferences) {
    const fruitId = Number(preference.fruit_id)
    const score = Number(preference.preference_score)

    if (preference.is_forbidden) {
      selection.forbiddenIds.push(fruitId)
    } else if (score === 2) {
      selection.favoriteIds.push(fruitId)
    } else if (score !== 0) {
      selection.legacyPreferences.push({
        fruit_id: fruitId,
        preference_score: preference.preference_score,
        is_forbidden: false,
      })
    }
  }

  selection.favoriteIds.sort((left, right) => left - right)
  selection.forbiddenIds.sort((left, right) => left - right)
  selection.legacyPreferences.sort((left, right) => left.fruit_id - right.fruit_id)
  return selection
}

export function selectionToPreferences(selection) {
  const preferences = new Map(
    (selection.legacyPreferences ?? []).map((preference) => [
      Number(preference.fruit_id),
      {
        fruit_id: Number(preference.fruit_id),
        preference_score: preference.preference_score,
        is_forbidden: false,
      },
    ]),
  )

  for (const fruitId of selection.favoriteIds ?? []) {
    preferences.set(Number(fruitId), {
      fruit_id: Number(fruitId),
      preference_score: 2,
      is_forbidden: false,
    })
  }

  for (const fruitId of selection.forbiddenIds ?? []) {
    preferences.set(Number(fruitId), {
      fruit_id: Number(fruitId),
      preference_score: 0,
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
    city: '',
    region: '全国',
    sweet_preference: 0.5,
    sour_preference: 0.5,
    soft_preference: 0.5,
    crisp_preference: 0.5,
    price_level: 2,
    convenience_preference: 0.5,
  }
}

export function profileFromUser(user) {
  const profile = createDefaultProfile()

  for (const key of Object.keys(profile)) {
    profile[key] = user[key]
  }

  return profile
}
