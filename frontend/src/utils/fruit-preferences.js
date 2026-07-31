export const FRUIT_PREFERENCE_OPTIONS = [
  { value: 'neutral', label: '无所谓' },
  { value: 'favorite', label: '非常喜欢' },
  { value: 'like', label: '喜欢' },
  { value: 'dislike', label: '不喜欢' },
  { value: 'forbidden', label: '不能食用' },
]

export function preferencesToState(preferences) {
  return Object.fromEntries(
    preferences.map((preference) => {
      let state = 'neutral'

      if (preference.is_forbidden) {
        state = 'forbidden'
      } else if (preference.preference_score === 2) {
        state = 'favorite'
      } else if (preference.preference_score === 1) {
        state = 'like'
      } else if (preference.preference_score === -1) {
        state = 'dislike'
      }

      return [preference.fruit_id, state]
    }),
  )
}

export function stateToPreferences(preferenceState) {
  return Object.entries(preferenceState)
    .filter(([, state]) => state !== 'neutral')
    .map(([fruitId, state]) => ({
      fruit_id: Number(fruitId),
      preference_score:
        state === 'favorite' ? 2 : state === 'like' ? 1 : state === 'dislike' ? -1 : 0,
      is_forbidden: state === 'forbidden',
    }))
    .sort((left, right) => left.fruit_id - right.fruit_id)
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
