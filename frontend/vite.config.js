import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import {
  GITHUB_PAGES_TARGET,
  githubPagesHtml,
  resolvePagesBase,
  resolvePagesOrigin,
  validateGitHubPagesEnvironment,
} from './build/github-pages.js'
import { sites } from './build/sites-vite-plugin.js'

export default defineConfig(async ({ mode }) => {
  const isGitHubPages = process.env.DEPLOY_TARGET === GITHUB_PAGES_TARGET
  const base = isGitHubPages
    ? resolvePagesBase(process.env.GITHUB_REPOSITORY)
    : '/'

  if (isGitHubPages) {
    const env = loadEnv(mode, process.cwd(), 'VITE_')
    validateGitHubPagesEnvironment({
      apiBaseUrl:
        process.env.VITE_API_BASE_URL ?? env.VITE_API_BASE_URL ?? '',
      supabaseUrl:
        process.env.VITE_SUPABASE_URL ?? env.VITE_SUPABASE_URL ?? '',
      publishableKey:
        process.env.VITE_SUPABASE_PUBLISHABLE_KEY ??
        env.VITE_SUPABASE_PUBLISHABLE_KEY ??
        '',
    })
  }

  process.env.WRANGLER_WRITE_LOGS ??= 'false'
  process.env.WRANGLER_LOG_PATH ??= '.wrangler/logs'
  process.env.MINIFLARE_REGISTRY_PATH ??= '.wrangler/registry'

  const plugins = [vue()]

  if (isGitHubPages) {
    plugins.push(
      githubPagesHtml({
        siteOrigin: resolvePagesOrigin({
          owner: process.env.GITHUB_REPOSITORY_OWNER,
          base,
        }),
      }),
    )
  } else {
    const { cloudflare } = await import('@cloudflare/vite-plugin')
    plugins.push(sites(), cloudflare())
  }

  return {
    base,
    define: {
      __DAILY_FRUIT_GITHUB_PAGES__: JSON.stringify(isGitHubPages),
    },
    plugins,
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
