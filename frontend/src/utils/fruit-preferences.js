export function createDefaultFruitPreferenceSelection() {
  return {
    favoriteIds: [],
    forbiddenIds: [],
    triedIds: [],
    notTriedIds: [],
    willingToTryIds: [],
    notWillingToTryIds: [],
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

    if (preference.has_tried === true) selection.triedIds.push(fruitId)
    if (preference.has_tried === false) selection.notTriedIds.push(fruitId)
    if (preference.willing_to_try === true) selection.willingToTryIds.push(fruitId)
    if (preference.willing_to_try === false) selection.notWillingToTryIds.push(fruitId)
  }

  selection.favoriteIds.sort((left, right) => left - right)
  selection.forbiddenIds.sort((left, right) => left - right)
  selection.triedIds.sort((left, right) => left - right)
  selection.notTriedIds.sort((left, right) => left - right)
  selection.willingToTryIds.sort((left, right) => left - right)
  selection.notWillingToTryIds.sort((left, right) => left - right)
  selection.legacyPreferences.sort((left, right) => left.fruit_id - right.fruit_id)
  return selection
}

export function selectionToPreferences(selection) {
  const notTriedIds = new Set(selection.notTriedIds ?? [])
  const favoriteIds = (selection.favoriteIds ?? []).filter(
    (fruitId) => !notTriedIds.has(Number(fruitId)),
  )
  const preferences = new Map(
    (selection.legacyPreferences ?? []).map((preference) => [
      Number(preference.fruit_id),
      {
        fruit_id: Number(preference.fruit_id),
        preference_score: preference.preference_score,
        is_forbidden: false,
        has_tried: preference.has_tried ?? null,
        willing_to_try: preference.willing_to_try ?? null,
      },
    ]),
  )

  for (const fruitId of favoriteIds) {
    preferences.set(Number(fruitId), {
      fruit_id: Number(fruitId),
      preference_score: 2,
      is_forbidden: false,
      has_tried: selection.triedIds?.includes(Number(fruitId))
        ? true
        : selection.notTriedIds?.includes(Number(fruitId))
          ? false
          : null,
      willing_to_try: selection.willingToTryIds?.includes(Number(fruitId))
        ? true
        : selection.notWillingToTryIds?.includes(Number(fruitId))
          ? false
          : null,
    })
  }

  for (const fruitId of selection.forbiddenIds ?? []) {
    preferences.set(Number(fruitId), {
      fruit_id: Number(fruitId),
      preference_score: null,
      is_forbidden: true,
      has_tried: selection.triedIds?.includes(Number(fruitId))
        ? true
        : selection.notTriedIds?.includes(Number(fruitId))
          ? false
          : null,
      willing_to_try: selection.willingToTryIds?.includes(Number(fruitId))
        ? true
        : selection.notWillingToTryIds?.includes(Number(fruitId))
          ? false
          : null,
    })
  }

  for (const fruitId of selection.triedIds ?? []) {
    const id = Number(fruitId)
    const current = preferences.get(id) ?? {
      fruit_id: id,
      preference_score: null,
      is_forbidden: false,
      has_tried: null,
      willing_to_try: null,
    }
    current.has_tried = true
    preferences.set(id, current)
  }

  for (const fruitId of selection.notTriedIds ?? []) {
    const id = Number(fruitId)
    const current = preferences.get(id) ?? {
      fruit_id: id,
      preference_score: null,
      is_forbidden: false,
      has_tried: null,
      willing_to_try: null,
    }
    current.has_tried = false
    preferences.set(id, current)
  }

  for (const fruitId of selection.willingToTryIds ?? []) {
    const id = Number(fruitId)
    const current = preferences.get(id) ?? {
      fruit_id: id,
      preference_score: null,
      is_forbidden: false,
      has_tried: null,
      willing_to_try: null,
    }
    current.willing_to_try = true
    preferences.set(id, current)
  }

  for (const fruitId of selection.notWillingToTryIds ?? []) {
    const id = Number(fruitId)
    const current = preferences.get(id) ?? {
      fruit_id: id,
      preference_score: null,
      is_forbidden: false,
      has_tried: null,
      willing_to_try: null,
    }
    current.willing_to_try = false
    preferences.set(id, current)
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
    discovery_level: 1,
  }
}

export function profileFromUser(user) {
  const profile = createDefaultProfile()

  for (const key of Object.keys(profile)) {
    if (user[key] !== undefined && user[key] !== null) profile[key] = user[key]
  }

  return profile
}
