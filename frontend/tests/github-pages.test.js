import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  githubPagesHtml,
  resolvePagesBase,
  resolvePagesOrigin,
  validateGitHubPagesEnvironment,
  validatePublishableKey,
  validatePublicApiBaseUrl,
  validatePublicSupabaseUrl,
} from '../build/github-pages.js'

test('GitHub Pages base is derived from the repository with a local fallback', () => {
  assert.equal(resolvePagesBase('dreamqwq114-del/daily-fruit'), '/daily-fruit/')
  assert.equal(resolvePagesBase(undefined), '/daily-fruit/')
})

test('Pages deployment requires all three public runtime values', () => {
  assert.deepEqual(
    validateGitHubPagesEnvironment({
      apiBaseUrl: 'https://api.example.com/',
      supabaseUrl: 'https://project.supabase.co/',
      publishableKey: 'sb_publishable_example',
    }),
    {
      apiBaseUrl: 'https://api.example.com',
      supabaseUrl: 'https://project.supabase.co',
      publishableKey: 'sb_publishable_example',
    },
  )
  assert.throws(() =>
    validateGitHubPagesEnvironment({
      apiBaseUrl: '',
      supabaseUrl: 'https://project.supabase.co',
      publishableKey: 'sb_publishable_example',
    }),
  )
  assert.throws(() =>
    validateGitHubPagesEnvironment({
      apiBaseUrl: 'https://api.example.com',
      supabaseUrl: '',
      publishableKey: 'sb_publishable_example',
    }),
  )
  assert.throws(() =>
    validateGitHubPagesEnvironment({
      apiBaseUrl: 'https://api.example.com',
      supabaseUrl: 'https://project.supabase.co',
      publishableKey: '',
    }),
  )
})

test('Supabase public values reject insecure URLs and secret-like keys', () => {
  assert.equal(
    validatePublicSupabaseUrl('https://project.supabase.co/'),
    'https://project.supabase.co',
  )
  assert.throws(() => validatePublicSupabaseUrl('http://project.supabase.co'))
  assert.throws(() => validatePublicSupabaseUrl('https://localhost:54321'))
  assert.equal(
    validatePublishableKey(' sb_publishable_example '),
    'sb_publishable_example',
  )
  assert.throws(() => validatePublishableKey('sb_secret_example'))
  assert.throws(() => validatePublishableKey('legacy-anon-key'))
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
