// 用户资料 API 的唯一前端入口。组件只传 JSON payload；认证 header、
// 超时、401 处理和错误映射统一由 apiRequest 完成。
import { apiRequest } from './http.js'

export function createUser(payload) {
  // POST /api/me 创建当前 JWT 对应的 public.users 行。
  return apiRequest('/api/me', { method: 'POST', body: payload })
}

export function getUser() {
  // GET /api/me 读取当前用户，404 表示还未完成建档。
  return apiRequest('/api/me')
}

export function updateUser(payload) {
  // PUT /api/me 只提交 profile 中明确需要保存的字段。
  return apiRequest('/api/me', { method: 'PUT', body: payload })
}

export function getFruitPreferences() {
  // GET /api/me/fruit-preferences 返回当前用户偏好行。
  return apiRequest('/api/me/fruit-preferences')
}

export function getFruitOptionPreferences() {
  return apiRequest('/api/me/fruit-option-preferences')
}

export function replaceFruitPreferences(preferences, optionPreferences) {
  // PUT 使用后端 merge 语义，不会把熟悉度字段重置为默认值。
  return apiRequest('/api/me/fruit-preferences', {
    method: 'PUT',
    body: {
      preferences,
      ...(optionPreferences === undefined
        ? {}
        : { option_preferences: optionPreferences }),
    },
  })
}
