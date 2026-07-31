import test from 'node:test'
import assert from 'node:assert/strict'

import { getAuthErrorMessage } from '../src/auth/errors.js'

test('maps known Supabase Auth errors to Chinese', () => {
  assert.equal(getAuthErrorMessage({ code: 'user_already_exists' }), '该邮箱已注册，请直接登录。')
  assert.equal(getAuthErrorMessage({ code: 'invalid_credentials' }), '邮箱或密码错误。')
  assert.equal(getAuthErrorMessage({ code: 'weak_password' }), '密码至少需要 8 位。')
  assert.equal(getAuthErrorMessage({ code: 'over_email_send_rate_limit' }), '请求过于频繁，请稍后再试。')
  assert.equal(getAuthErrorMessage({ code: 'signup_disabled' }), '注册服务暂时不可用，请稍后再试。')
  assert.equal(getAuthErrorMessage({ status: 503 }), '登录服务暂时不可用，请稍后再试。')
})

test('does not expose unknown English auth errors', () => {
  assert.equal(
    getAuthErrorMessage(new Error('unexpected internal auth failure')),
    '注册或登录没有成功，请检查输入后重试。',
  )
})
