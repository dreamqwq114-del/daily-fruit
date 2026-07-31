import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  githubPagesHtml,
  resolvePagesBase,
  resolvePagesOrigin,
  validatePublicApiBaseUrl,
} from '../build/github-pages.js'

test('GitHub Pages base is derived from the repository with a local fallback', () => {
  assert.equal(resolvePagesBase('dreamqwq114-del/daily-fruit'), '/daily-fruit/')
  assert.equal(resolvePagesBase(undefined), '/daily-fruit/')
})

test('GitHub Pages origin includes the project path', () => {
  assert.equal(
    resolvePagesOrigin({
      owner: 'dreamqwq114-del',
      base: '/daily-fruit/',
    }),
    'https://dreamqwq114-del.github.io/daily-fruit',
  )
})

test('public api base accepts HTTPS and rejects local or insecure URLs', () => {
  assert.equal(validatePublicApiBaseUrl(''), '')
  assert.equal(
    validatePublicApiBaseUrl('https://api.example.com/'),
    'https://api.example.com',
  )
  assert.throws(() => validatePublicApiBaseUrl('http://api.example.com'))
  assert.throws(() => validatePublicApiBaseUrl('https://localhost:8000'))
  assert.throws(() => validatePublicApiBaseUrl('https://localhost.:8000'))
  assert.throws(() => validatePublicApiBaseUrl('https://[::1]:8000'))
  assert.throws(() => validatePublicApiBaseUrl('https://0.0.0.0:8000'))
  assert.throws(() =>
    validatePublicApiBaseUrl('https://user:password@api.example.com'),
  )
  assert.throws(() => validatePublicApiBaseUrl('https://api.example.com?token=x'))
  assert.throws(() => validatePublicApiBaseUrl('https://api.example.com#debug'))
})

test('Pages HTML replaces the Sites-only origin placeholder', () => {
  const plugin = githubPagesHtml({
    siteOrigin: 'https://dreamqwq114-del.github.io/daily-fruit',
  })

  assert.equal(
    plugin.transformIndexHtml('<meta content="__SITE_ORIGIN__/og.png">'),
    '<meta content="https://dreamqwq114-del.github.io/daily-fruit/og.png">',
  )
})
