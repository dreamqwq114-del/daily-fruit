import assert from 'node:assert/strict'
import { afterEach, beforeEach, test } from 'node:test'

import {
  preferencesToState,
  stateToPreferences,
} from '../src/utils/fruit-preferences.js'
import {
  clearUserId,
  getUserId,
  setUserId,
  USER_ID_KEY,
} from '../src/utils/user-session.js'

class MemoryStorage {
  #values = new Map()

  getItem(key) {
    return this.#values.get(key) ?? null
  }

  setItem(key, value) {
    this.#values.set(key, String(value))
  }

  removeItem(key) {
    this.#values.delete(key)
  }
}

globalThis.window = {
  localStorage: new MemoryStorage(),
  setTimeout: globalThis.setTimeout,
  clearTimeout: globalThis.clearTimeout,
}

const { ApiError, apiRequest } = await import('../src/api/http.js')

beforeEach(() => {
  clearUserId()
})

afterEach(() => {
  delete globalThis.fetch
})

test('user session accepts only positive safe integer ids', () => {
  setUserId(12)
  assert.equal(getUserId(), 12)

  window.localStorage.setItem(USER_ID_KEY, '1.5')
  assert.equal(getUserId(), null)

  window.localStorage.setItem(USER_ID_KEY, '-3')
  assert.equal(getUserId(), null)
})

test('fruit preference mapping keeps one normalized state per fruit', () => {
  const state = preferencesToState([
    { fruit_id: 1, preference_score: 2, is_forbidden: false },
    { fruit_id: 2, preference_score: -1, is_forbidden: false },
    { fruit_id: 3, preference_score: 2, is_forbidden: true },
  ])

  assert.deepEqual(state, {
    1: 'favorite',
    2: 'dislike',
    3: 'forbidden',
  })

  assert.deepEqual(
    stateToPreferences({ 1: 'favorite', 2: 'neutral', 3: 'forbidden' }),
    [
      { fruit_id: 1, preference_score: 2, is_forbidden: false },
      { fruit_id: 3, preference_score: 0, is_forbidden: true },
    ],
  )
})

test('apiRequest returns json for successful responses', async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ status: 'ok' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })

  assert.deepEqual(await apiRequest('/health'), { status: 'ok' })
})

test('apiRequest exposes safe conflict details and status', async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: '当前没有可刷新的推荐' }), {
      status: 409,
      headers: { 'Content-Type': 'application/json' },
    })

  await assert.rejects(
    () => apiRequest('/api/recommendations/refresh'),
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
    () => apiRequest('/api/fruits'),
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
    () => apiRequest('/api/fruits'),
    (error) => {
      assert.ok(error instanceof ApiError)
      assert.equal(error.code, 'invalid_response')
      assert.equal(error.message, '服务返回了无法识别的内容，请稍后重试。')
      return true
    },
  )
})
