// 所有业务请求经过这里：读取 token、设置 JSON header、超时、解析错误、
// 处理 401 和阻止生产环境请求访问者自己的 localhost。
import { clearLocalSession, getAccessToken } from '../auth/session.js'

const DEFAULT_TIMEOUT_MS = 10_000
const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL ?? '')
  .trim()
  .replace(/\/+$/, '')
const IS_DEVELOPMENT = import.meta.env?.DEV ?? true
const IS_GITHUB_PAGES =
  typeof __DAILY_FRUIT_GITHUB_PAGES__ !== 'undefined' &&
  __DAILY_FRUIT_GITHUB_PAGES__

const STATUS_MESSAGES = {
  400: '请求内容有误，请检查后重试。',
  401: '登录状态已过期，请重新登录。',
  404: '没有找到对应的数据。',
  409: '当前条件下无法完成操作，请调整后重试。',
  422: '填写的信息不完整或格式不正确。',
  429: '操作太频繁，请稍后再试。',
  500: '服务暂时出现问题，请稍后再试。',
  503: '数据服务暂时不可用，请稍后重试。',
}

export class ApiError extends Error {
  // 让页面根据 status/code 展示友好信息，而不是暴露后端堆栈。
  constructor(message, { status = 0, code = 'request_failed' } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export function ensureApiConfigured({
  apiBaseUrl = API_BASE_URL,
  isDevelopment = IS_DEVELOPMENT,
  isGitHubPages = IS_GITHUB_PAGES,
} = {}) {
  // GitHub Pages 没有后端时在 fetch 前失败，避免向错误地址发请求。
  if (isGitHubPages && !apiBaseUrl && !isDevelopment) {
    throw new ApiError('在线服务尚未配置', {
      code: 'api_not_configured',
    })
  }
}

function getResponseMessage(status, payload) {
  // 只接受少量安全的后端 detail；其他状态统一使用前端文案。
  if (
    payload &&
    typeof payload.detail === 'string' &&
    [404, 409, 503].includes(status)
  ) {
    return payload.detail
  }

  return STATUS_MESSAGES[status] ?? '请求没有成功，请稍后重试。'
}

function notifyAuthenticationRequired() {
  window.dispatchEvent(new Event('daily-fruit:auth-required'))
}

export async function handleAuthenticationRequired({
  clearSession = clearLocalSession,
  notify = notifyAuthenticationRequired,
} = {}) {
  // 清理失效会话后通知路由层回到登录页；清理失败也不能卡住跳转。
  try {
    await clearSession()
  } catch {
    // A stale local session must not prevent the route from returning to login.
  } finally {
    notify()
  }
}

async function readPayload(response) {
  // 先读取文本再按 content-type 解析，避免 HTML 错误页被当作 JSON。
  const contentType = response.headers.get('content-type') ?? ''
  const text = await response.text()

  if (contentType.includes('application/json')) {
    if (!text) return null

    try {
      return JSON.parse(text)
    } catch {
      throw new ApiError('服务返回的数据格式不正确，请稍后重试。', {
        status: response.status,
        code: 'invalid_response',
      })
    }
  }

  if (response.ok) {
    throw new ApiError('服务返回了无法识别的内容，请稍后重试。', {
      status: response.status,
      code: 'invalid_response',
    })
  }

  return text ? { detail: text } : null
}

export async function apiRequest(
  path,
  {
    method = 'GET',
    body,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    signal,
    accessToken: suppliedAccessToken,
  } = {},
) {
  // 业务 API 只使用 Bearer token；credentials=omit 防止浏览器自动带 cookie。
  ensureApiConfigured()

  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort('timeout'), timeoutMs)
  const abortFromCaller = () => controller.abort('cancelled')
  signal?.addEventListener('abort', abortFromCaller, { once: true })

  try {
    const accessToken = suppliedAccessToken ?? await getAccessToken()
    if (!accessToken) {
      notifyAuthenticationRequired()
      throw new ApiError('请先登录后再继续。', {
        status: 401,
        code: 'login_required',
      })
    }
    const headers = { Authorization: `Bearer ${accessToken}` }
    if (body !== undefined) headers['Content-Type'] = 'application/json'
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'omit',
      signal: controller.signal,
    })
    const payload = response.status === 204 ? null : await readPayload(response)

    if (!response.ok) {
      if (response.status === 401) {
        await handleAuthenticationRequired()
      }
      throw new ApiError(getResponseMessage(response.status, payload), {
        status: response.status,
        code: 'http_error',
      })
    }

    return payload
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }

    if (controller.signal.aborted) {
      const timedOut = controller.signal.reason === 'timeout'
      throw new ApiError(
        timedOut ? '请求超时，请检查网络后重试。' : '请求已取消。',
        { code: timedOut ? 'timeout' : 'cancelled' },
      )
    }

    throw new ApiError('无法连接服务，请确认后端已启动并检查网络。', {
      code: 'network',
    })
  } finally {
    window.clearTimeout(timeoutId)
    signal?.removeEventListener('abort', abortFromCaller)
  }
}

export { API_BASE_URL, DEFAULT_TIMEOUT_MS }
