// Supabase Auth 的英文 code/message 映射为可直接展示的中文；未知错误
// 不回显原始服务端文本，避免泄漏内部细节或把英文堆栈展示给用户。
const AUTH_ERROR_MESSAGES = {
  email_exists: '该邮箱已注册，请直接登录。',
  user_already_exists: '该邮箱已注册，请直接登录。',
  invalid_credentials: '邮箱或密码错误。',
  weak_password: '密码至少需要 8 位。',
  over_email_send_rate_limit: '请求过于频繁，请稍后再试。',
  over_request_rate_limit: '请求过于频繁，请稍后再试。',
  signup_disabled: '注册服务暂时不可用，请稍后再试。',
  email_provider_disabled: '邮箱登录服务暂时不可用。',
}

export function getAuthErrorMessage(error) {
  // 优先使用稳定 code，再对少量已知英文 message 做兼容匹配。
  if (AUTH_ERROR_MESSAGES[error?.code]) return AUTH_ERROR_MESSAGES[error.code]

  const message = String(error?.message || '').toLowerCase()
  if (message.includes('already registered') || message.includes('already exists')) {
    return AUTH_ERROR_MESSAGES.user_already_exists
  }
  if (message.includes('invalid login credentials')) {
    return AUTH_ERROR_MESSAGES.invalid_credentials
  }
  if (message.includes('password') && (message.includes('characters') || message.includes('weak'))) {
    return AUTH_ERROR_MESSAGES.weak_password
  }
  if (error?.status === 429 || message.includes('rate limit')) {
    return AUTH_ERROR_MESSAGES.over_request_rate_limit
  }
  if (error?.status >= 500 || error instanceof TypeError || message.includes('fetch')) {
    return '登录服务暂时不可用，请稍后再试。'
  }
  return '注册或登录没有成功，请检查输入后重试。'
}
