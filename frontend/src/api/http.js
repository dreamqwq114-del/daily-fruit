const DEFAULT_TIMEOUT_MS = 10_000
const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

const STATUS_MESSAGES = {
  400: '请求内容有误，请检查后重试。',
  404: '没有找到对应的数据。',
  409: '当前条件下无法完成操作，请调整后重试。',
  422: '填写的信息不完整或格式不正确。',
  429: '操作太频繁，请稍后再试。',
  500: '服务暂时出现问题，请稍后再试。',
  503: '数据服务暂时不可用，请稍后重试。',
}

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'request_failed' } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

function getResponseMessage(status, payload) {
  if (
    payload &&
    typeof payload.detail === 'string' &&
    [404, 409, 503].includes(status)
  ) {
    return payload.detail
  }

  return STATUS_MESSAGES[status] ?? '请求没有成功，请稍后重试。'
}

async function readPayload(response) {
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
  { method = 'GET', body, timeoutMs = DEFAULT_TIMEOUT_MS, signal } = {},
) {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort('timeout'), timeoutMs)
  const abortFromCaller = () => controller.abort('cancelled')
  signal?.addEventListener('abort', abortFromCaller, { once: true })

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'omit',
      signal: controller.signal,
    })
    const payload = response.status === 204 ? null : await readPayload(response)

    if (!response.ok) {
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
