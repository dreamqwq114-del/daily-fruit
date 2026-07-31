import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { sites } from './build/sites-vite-plugin.js'

export default defineConfig(async () => {
  process.env.WRANGLER_WRITE_LOGS ??= 'false'
  process.env.WRANGLER_LOG_PATH ??= '.wrangler/logs'
  process.env.MINIFLARE_REGISTRY_PATH ??= '.wrangler/registry'

  const { cloudflare } = await import('@cloudflare/vite-plugin')

  return {
    plugins: [vue(), sites(), cloudflare()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target:
            process.env.DAILY_FRUIT_API_PROXY_TARGET ??
            'http://127.0.0.1:8000',
        },
        '/health': {
          target:
            process.env.DAILY_FRUIT_API_PROXY_TARGET ??
            'http://127.0.0.1:8000',
        },
      },
    },
  }
})
