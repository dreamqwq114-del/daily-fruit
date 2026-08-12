import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { afterEach, test } from 'node:test'

import {
  createDefaultProfile,
  preferencesToSelection,
  profileFromUser,
  profileToApiPayload,
  SENSORY_ANCHORS,
  selectionToPreferences,
} from '../src/utils/fruit-preferences.js'
import {
  optionQuickChoices,
  selectionOptionHint,
} from '../src/utils/selection-option-ui.js'
globalThis.window = {
  setTimeout: globalThis.setTimeout,
  clearTimeout: globalThis.clearTimeout,
  dispatchEvent: () => {},
}

const {
  ApiError,
  apiRequest,
  ensureApiConfigured,
  handleAuthenticationRequired,
} = await import(
  '../src/api/http.js'
)

afterEach(() => {
  delete globalThis.fetch
})

test('fruit preference mapping uses favorite, dislike and forbidden selections', () => {
  const selection = preferencesToSelection([
    { fruit_id: 1, preference_score: 2, is_forbidden: false },
    { fruit_id: 2, preference_score: -1, is_forbidden: false },
    { fruit_id: 3, preference_score: 2, is_forbidden: true },
  ])

  assert.deepEqual(selection, {
    favoriteIds: [1],
    dislikeIds: [2],
    forbiddenIds: [3],
  })

  assert.deepEqual(
    selectionToPreferences(selection),
    [
      { fruit_id: 1, preference_score: 2, is_forbidden: false, has_tried: true },
      { fruit_id: 2, preference_score: -1, is_forbidden: false },
      { fruit_id: 3, preference_score: null, is_forbidden: true },
    ],
  )
})

test('unselected fruits are not submitted as neutral preferences', () => {
  assert.deepEqual(
    selectionToPreferences({
      favoriteIds: [2],
      dislikeIds: [],
      forbiddenIds: [],
    }),
    [{ fruit_id: 2, preference_score: 2, is_forbidden: false, has_tried: true }],
  )
})

test('real selection-option seed respects the supplied matching policy', () => {
  const seedRows = JSON.parse(
    readFileSync(
      new URL('../../data/fruit_selection_options_seed.json', import.meta.url),
      'utf8',
    ),
  )
  const expectedLabels = {
    apple: '根据我的质地偏好自动选择',
    peach: '根据我的质地偏好自动选择',
    grape: '根据我的质地偏好自动选择',
    kiwifruit: '根据我的甜酸偏好自动选择',
    pomegranate: '不设置类型偏好',
    dragon_fruit: '不设置类型偏好',
  }

  let fruitId = 1
  for (const [code, expectedLabel] of Object.entries(expectedLabels)) {
    const selectionOptions = seedRows
      .filter((row) => row.fruit_code === code)
      .map((row, optionIndex) => ({
        ...row,
        id: fruitId * 100 + optionIndex,
        fruit_id: fruitId,
      }))
    const selectionMatchingMode =
      code === 'kiwifruit'
        ? 'sweet-sour'
        : code === 'pomegranate' || code === 'dragon_fruit'
          ? 'explicit-only'
          : 'texture'
    const fruit = {
      id: fruitId,
      code,
      selection_matching_mode: selectionMatchingMode,
      selection_option_score_effect:
        code === 'pomegranate' ? 'filter-only' : 'profile-override',
      selection_options: selectionOptions,
    }

    assert.equal(optionQuickChoices(fruit, [])[0].label, expectedLabel)
    if (code === 'pomegranate') {
      assert.match(selectionOptionHint(fruit), /不改变甜酸质地评分/)
    }
    if (code === 'dragon_fruit') {
      assert.match(selectionOptionHint(fruit), /参与评分/)
    }
    fruitId += 1
  }
})

test('profile defaults omit city and use the new region and horizon defaults', () => {
  const profile = profileFromUser({ city: '苏州', region: '全国' })
  assert.equal(profile.city, undefined)
  assert.equal(profile.region, 'UNKNOWN')
  assert.equal(profile.discovery_level, 1)
  assert.equal(profile.consumption_horizon_days, 4)
  assert.equal(createDefaultProfile().price_level, 2)
  assert.equal(createDefaultProfile().market_access_level, 2)
  assert.equal(createDefaultProfile().accepts_online_purchase, false)
  assert.equal(createDefaultProfile().sweet_preference, null)
  assert.equal(createDefaultProfile().texture_preference, null)
  assert.equal(profileFromUser({ texture_preference: null }).texture_preference, null)
  assert.equal(profileFromUser({ soft_preference: 0.2, crisp_preference: 0.8 }).texture_preference, 0.8)
  assert.equal(profileFromUser({ soft_preference: 0.1, crisp_preference: 0.1 }).texture_preference, null)
  assert.equal(profileToApiPayload(createDefaultProfile()).texture_preference, undefined)
  const cleared = createDefaultProfile()
  cleared.__explicitlyChangedPreferences.add('texture_preference')
  assert.equal(profileToApiPayload(cleared).texture_preference, null)
})

test('sensory anchors stay centralized and show five equally spaced labels', () => {
  assert.deepEqual(
    SENSORY_ANCHORS.texture_preference.map((anchor) => [anchor.name, anchor.percent]),
    [
      ['榴莲', '0%'],
      ['软桃', '25%'],
      ['火龙果', '50%'],
      ['梨', '75%'],
      ['清脆苹果', '100%'],
    ],
  )
})

test('apiRequest returns json for successful responses', async () => {
  let requestOptions
  globalThis.fetch = async (_url, options) => {
    requestOptions = options
    return new Response(JSON.stringify({ status: 'ok' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  assert.deepEqual(
    await apiRequest('/health', { accessToken: 'test-access-token' }),
    { status: 'ok' },
  )
  assert.equal(requestOptions.headers.Authorization, 'Bearer test-access-token')
})

test('apiRequest refuses protected requests without a session', async () => {
  let called = false
  globalThis.fetch = async () => {
    called = true
  }

  await assert.rejects(
    () => apiRequest('/api/fruits'),
    (error) => error instanceof ApiError && error.code === 'login_required',
  )
  assert.equal(called, false)
})

test('authentication redirect waits for local session cleanup', async () => {
  const order = []
  let finishCleanup
  const cleanup = new Promise((resolve) => {
    finishCleanup = () => {
      order.push('cleared')
      resolve()
    }
  })

  const handling = handleAuthenticationRequired({
    clearSession: () => cleanup,
    notify: () => order.push('notified'),
  })
  await Promise.resolve()
  assert.deepEqual(order, [])

  finishCleanup()
  await handling
  assert.deepEqual(order, ['cleared', 'notified'])
})

test('authentication redirect still runs after local cleanup fails', async () => {
  const order = []
  await handleAuthenticationRequired({
    clearSession: async () => {
      order.push('cleanup-failed')
      throw new Error('storage unavailable')
    },
    notify: () => order.push('notified'),
  })
  assert.deepEqual(order, ['cleanup-failed', 'notified'])
})

test('production requests stop before fetch when no public api is configured', () => {
  let called = false
  globalThis.fetch = async () => {
    called = true
  }

  assert.throws(
    () =>
      ensureApiConfigured({
        apiBaseUrl: '',
        isDevelopment: false,
        isGitHubPages: true,
      }),
    (error) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.code, 'api_not_configured')
      assert.equal(error.message, '在线服务尚未配置')
      return true
    },
  )
  assert.equal(called, false)
})

test('non-Pages production builds keep their existing relative API behavior', () => {
  assert.doesNotThrow(() =>
    ensureApiConfigured({
      apiBaseUrl: '',
      isDevelopment: false,
      isGitHubPages: false,
    }),
  )
})

test('apiRequest exposes safe conflict details and status', async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: '当前没有可刷新的推荐' }), {
      status: 409,
      headers: { 'Content-Type': 'application/json' },
    })

  await assert.rejects(
    () => apiRequest('/api/recommendations/refresh', { accessToken: 'test-access-token' }),
    (error) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.status, 409)
      assert.equal(error.message, '当前没有可刷新的推荐')
      return true
    },
  )
})

test('apiRequest turns fetch failures into friendly network errors', async () => {
  globalThis.fetch = async () => {
    throw new TypeError('socket details must not leak')
  }

  await assert.rejects(
    () => apiRequest('/api/fruits', { accessToken: 'test-access-token' }),
    (error) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.code, 'network')
      assert.equal(error.message, '无法连接服务，请确认后端已启动并检查网络。')
      return true
    },
  )
})

test('apiRequest rejects successful html fallbacks as invalid responses', async () => {
  globalThis.fetch = async () =>
    new Response('<!doctype html><div id="app"></div>', {
      status: 200,
      headers: { 'Content-Type': 'text/html' },
    })

  await assert.rejects(
    () => apiRequest('/api/fruits', { accessToken: 'test-access-token' }),
    (error) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.code, 'invalid_response')
      assert.equal(error.message, '服务返回了无法识别的内容，请稍后重试。')
      return true
    },
  )
})

test('apiRequest aborts requests that exceed the timeout', async () => {
  globalThis.fetch = async (_url, options) =>
    new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => {
        reject(new DOMException('aborted', 'AbortError'))
      })
    })

  await assert.rejects(
    () => apiRequest('/api/fruits', { timeoutMs: 5, accessToken: 'test-access-token' }),
    (error) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.code, 'timeout')
      assert.equal(error.message, '请求超时，请检查网络后重试。')
      return true
    },
  )
})
