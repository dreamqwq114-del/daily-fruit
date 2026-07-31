import assert from 'node:assert/strict'
import test from 'node:test'

import worker from '../worker/index.js'

function createAssets() {
  const requestedPaths = []

  return {
    requestedPaths,
    async fetch(request) {
      const path = new URL(request.url).pathname
      requestedPaths.push(path)

      if (path === '/index.html') {
        return new Response(
          '<meta property="og:url" content="__SITE_ORIGIN__"><div id="app"></div>',
          { status: 200, headers: { 'Content-Type': 'text/html' } },
        )
      }

      return new Response('not found', { status: 404 })
    },
  }
}

test('worker returns the app shell for direct browser routes', async () => {
  const assets = createAssets()
  const response = await worker.fetch(
    new Request('https://daily-fruit.example/onboarding', {
      headers: { Accept: 'text/html,application/xhtml+xml' },
    }),
    { ASSETS: assets },
  )

  assert.equal(response.status, 200)
  assert.deepEqual(assets.requestedPaths, ['/onboarding', '/index.html'])
  assert.match(await response.text(), /https:\/\/daily-fruit\.example/)
})

test('worker does not turn missing api requests into html', async () => {
  const assets = createAssets()
  const response = await worker.fetch(
    new Request('https://daily-fruit.example/api/fruits', {
      headers: { Accept: '*/*' },
    }),
    { ASSETS: assets },
  )

  assert.equal(response.status, 404)
  assert.deepEqual(assets.requestedPaths, ['/api/fruits'])
  assert.equal(await response.text(), 'not found')
})
