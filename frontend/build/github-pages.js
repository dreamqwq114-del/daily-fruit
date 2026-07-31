export const GITHUB_PAGES_TARGET = 'github-pages'
export const DEFAULT_REPOSITORY_NAME = 'daily-fruit'
export const DEFAULT_GITHUB_OWNER = 'dreamqwq114-del'

export function resolveRepositoryName(repository) {
  const name = repository?.split('/').filter(Boolean).at(-1)
  return name || DEFAULT_REPOSITORY_NAME
}

export function resolvePagesBase(repository) {
  return `/${resolveRepositoryName(repository)}/`
}

export function resolvePagesOrigin({ owner, base }) {
  const resolvedOwner = owner || DEFAULT_GITHUB_OWNER
  return `https://${resolvedOwner}.github.io${base.replace(/\/$/, '')}`
}

export function validatePublicApiBaseUrl(value) {
  const normalized = value.trim().replace(/\/$/, '')

  if (!normalized) return ''

  let url
  try {
    url = new URL(normalized)
  } catch {
    throw new Error('VITE_API_BASE_URL must be an absolute HTTPS URL.')
  }

  const hostname = url.hostname.toLowerCase().replace(/\.$/, '')

  if (
    url.protocol !== 'https:' ||
    ['localhost', '127.0.0.1', '[::1]', '0.0.0.0'].includes(hostname)
  ) {
    throw new Error(
      'VITE_API_BASE_URL must use HTTPS and must not point to localhost.',
    )
  }

  if (url.username || url.password || url.search || url.hash) {
    throw new Error(
      'VITE_API_BASE_URL must not include credentials, a query, or a hash.',
    )
  }

  return normalized
}

export function githubPagesHtml({ siteOrigin }) {
  return {
    name: 'github-pages-html',
    transformIndexHtml(html) {
      return html.replaceAll('__SITE_ORIGIN__', siteOrigin)
    },
  }
}
