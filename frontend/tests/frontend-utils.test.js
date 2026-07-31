import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'

import {
  preferencesToSelection,
  selectionToPreferences,
} from '../src/utils/fruit-preferences.js'
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

test('fruit preference mapping uses favorite and forbidden selections', () => {
  const selection = preferencesToSelection([
    { fruit_id: 1, preference_score: 2, is_forbidden: false },
    { fruit_id: 2, preference_score: -1, is_forbidden: false },
    { fruit_id: 3, preference_score: 2, is_forbidden: true },
  ])

  assert.deepEqual(selection, {
    favoriteIds: [1],
    forbiddenIds: [3],
    legacyPreferences: [
      { fruit_id: 2, preference_score: -1, is_forbidden: false },
    ],
  })

  assert.deepEqual(
    selectionToPreferences(selection),
    [
      { fruit_id: 1, preference_score: 2, is_forbidden: false },
      { fruit_id: 2, preference_score: -1, is_forbidden: false },
      { fruit_id: 3, preference_score: 0, is_forbidden: true },
    ],
  )
})

test('new selections override a legacy preference without dropping other legacy data', () => {
  assert.deepEqual(
    selectionToPreferences({
      favoriteIds: [2],
      forbiddenIds: [],
      legacyPreferences: [
        { fruit_id: 1, preference_score: -1, is_forbidden: false },
        { fruit_id: 2, preference_score: 1, is_forbidden: false },
      ],
    }),
    [
      { fruit_id: 1, preference_score: -1, is_forbidden: false },
      { fruit_id: 2, preference_score: 2, is_forbidden: false },
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
