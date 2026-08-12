// 消费类型只影响偏好页的展示与快捷操作。
// 推荐核心仍然读取 optionPreferences 中的 liked/disliked 记录。

function activeOptions(fruit) {
  return (fruit?.selection_options ?? []).filter((option) => option?.is_active)
}

function optionMode(fruit) {
  const declaredMode = fruit?.selection_matching_mode
  return declaredMode === 'texture' || declaredMode === 'sweet-sour'
    ? declaredMode
    : 'explicit-only'
}

function fruitPreferenceRows(fruit, preferences) {
  const fruitId = Number(fruit?.id)
  return (preferences ?? []).filter(
    (item) => Number(item?.fruit_id) === fruitId &&
      (item?.preference === 'liked' || item?.preference === 'disliked'),
  )
}

export function displayOptionName(option) {
  return option?.name ?? ''
}

export function optionPreferenceSummary(fruit, preferences) {
  const rows = fruitPreferenceRows(fruit, preferences)
  const liked = rows.filter((row) => row.preference === 'liked')
  const disliked = rows.filter((row) => row.preference === 'disliked')

  if (liked.length === 1 && disliked.length === 0) {
    const option = activeOptions(fruit).find((item) => Number(item.id) === Number(liked[0].option_id))
    if (option) {
      return optionMode(fruit) === 'texture'
        ? `优先${displayOptionName(option)}`
        : `只推荐${displayOptionName(option)}`
    }
  }

  if (rows.length === 0) {
    return optionMode(fruit) === 'explicit-only'
      ? '默认不设置类型偏好'
      : '根据口感偏好自动匹配'
  }
  return '自定义设置'
}

export function hasCustomOptionPreference(fruit, preferences) {
  const rows = fruitPreferenceRows(fruit, preferences)
  if (rows.length === 0) return false
  return rows.length !== 1 || rows[0].preference !== 'liked'
}

export function optionQuickChoices(fruit, preferences) {
  const options = activeOptions(fruit)
  const mode = optionMode(fruit)
  const isTasteMatched = mode === 'sweet-sour'
  const isExplicitOnly = mode === 'explicit-only'
  const choices = [{
    key: 'auto',
    label: isExplicitOnly
      ? '不设置类型偏好'
      : isTasteMatched
        ? '根据我的甜酸偏好自动选择'
        : '根据我的质地偏好自动选择',
    optionId: null,
  }]

  if (isTasteMatched || isExplicitOnly) {
    for (const option of options) {
      choices.push({
        key: `only-${option.id}`,
        label: `只推荐${displayOptionName(option)}`,
        optionId: Number(option.id),
      })
    }
    choices.push({ key: 'all', label: '各种类型都可以', optionId: null })
  } else {
    for (const option of options) {
      choices.push({
        key: `prefer-${option.id}`,
        label: `优先${displayOptionName(option)}`,
        optionId: Number(option.id),
      })
    }
    choices.push({ key: 'all', label: '两种都可以', optionId: null })
  }

  if (hasCustomOptionPreference(fruit, preferences)) {
    choices.push({ key: 'custom', label: '编辑详细设置', optionId: 'custom' })
  } else if (isTasteMatched || isExplicitOnly || options.length > 2) {
    choices.push({ key: 'custom', label: '自定义设置', optionId: 'custom' })
  }
  return choices
}

export function selectionOptionHint(fruit) {
  if (optionMode(fruit) !== 'explicit-only') return ''
  if (fruit?.selection_option_score_effect === 'filter-only') {
    return '仅用于明确喜欢/避开、过滤和推荐文案，不改变甜酸质地评分。'
  }
  if (fruit?.selection_option_score_effect === 'profile-override') {
    return '仅在你明确选择后生效；所选类型会使用对应口感与食用档案参与评分。'
  }
  return '仅在你明确选择后生效。'
}

export function optionRowsForFruit(fruit, preferences) {
  return fruitPreferenceRows(fruit, preferences)
}
