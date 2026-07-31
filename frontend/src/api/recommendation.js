import { apiRequest } from './http.js'

export function getTodayRecommendation(userId) {
  return apiRequest(`/api/recommendations/today?user_id=${userId}`)
}

export function refreshRecommendation(userId) {
  return apiRequest('/api/recommendations/refresh', {
    method: 'POST',
    body: { user_id: userId },
  })
}

export function listRecommendationHistory(userId, limit = 30) {
  return apiRequest(`/api/users/${userId}/recommendations?limit=${limit}`)
}

export function submitFeedback(itemId, feedbackType, comment = '') {
  return apiRequest(`/api/recommendations/items/${itemId}/feedback`, {
    method: 'POST',
    body: { feedback_type: feedbackType, comment },
  })
}
