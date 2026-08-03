// 消费类型只影响偏好页的展示与快捷操作。
// 推荐核心仍然读取 optionPreferences 中的 liked/disliked 记录。

const LABELS_BY_CODE = {
  crisp: '脆桃',
  soft: '软桃',
  green: '绿心',
  yellow: '黄心',
  red: '红心',
}

function activeOptions(fruit) {
  return (fruit?.selection_options ?? []).filter((option) => option?.is_active)
}

function fruitPreferenceRows(fruit, preferences) {
  const fruitId = Number(fruit?.id)
  return (preferences ?? []).filter(
    (item) => Number(item?.fruit_id) === fruitId &&
      (item?.preference === 'liked' || item?.preference === 'disliked'),
  )
}

export function displayOptionName(option) {
  return LABELS_BY_CODE[option?.code] ?? option?.name ?? ''
}

export function optionPreferenceSummary(fruit, preferences) {
  const rows = fruitPreferenceRows(fruit, preferences)
  const liked = rows.filter((row) => row.preference === 'liked')
  const disliked = rows.filter((row) => row.preference === 'disliked')

  if (liked.length === 1 && disliked.length === 0) {
    const option = activeOptions(fruit).find((item) => Number(item.id) === Number(liked[0].option_id))
    if (option) {
      return fruit?.code === 'peach' || option.code === 'crisp' || option.code === 'soft'
        ? `优先${displayOptionName(option)}`
        : `只推荐${displayOptionName(option)}`
    }
  }

  if (rows.length === 0) return '根据口感偏好自动匹配'
  return '自定义设置'
}

export function hasCustomOptionPreference(fruit, preferences) {
  const rows = fruitPreferenceRows(fruit, preferences)
  if (rows.length === 0) return false
  return rows.length !== 1 || rows[0].preference !== 'liked'
}

export function optionQuickChoices(fruit, preferences) {
  const options = activeOptions(fruit)
  const isKiwi = fruit?.code === 'kiwifruit' || options.some((option) => ['green', 'yellow', 'red'].includes(option.code))
  const choices = [{
    key: 'auto',
    label: isKiwi ? '根据我的甜酸偏好自动选择' : '根据我的软脆偏好自动选择',
    optionId: null,
  }]

  if (isKiwi) {
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
  } else if (fruit?.code === 'kiwifruit' || options.length > 2) {
    choices.push({ key: 'custom', label: '自定义设置', optionId: 'custom' })
  }
  return choices
}

export function optionRowsForFruit(fruit, preferences) {
  return fruitPreferenceRows(fruit, preferences)
}
