// 推荐 API 只描述 HTTP 方法和路径；认证、超时和错误处理由 apiRequest 统一完成。
import { apiRequest } from './http.js'

export function getTodayRecommendation() {
  // GET 会复用当天 active 记录。
  return apiRequest('/api/recommendations/today')
}

export function refreshRecommendation() {
  // POST 让后端负责替换旧组、递增刷新序号和避免相同组合。
  return apiRequest('/api/recommendations/refresh', {
    method: 'POST',
  })
}

export function listRecommendationHistory(limit = 30) {
  // 历史 limit 在后端限制为 1..100。
  return apiRequest(`/api/me/recommendations?limit=${limit}`)
}

export function submitFeedback(itemId, feedbackType, comment = '') {
  // itemId 来自当前用户的推荐详情；后端再次校验归属。
  return apiRequest(`/api/recommendations/items/${itemId}/feedback`, {
    method: 'POST',
    body: { feedback_type: feedbackType, comment },
  })
}
