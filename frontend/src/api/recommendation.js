import { apiRequest } from './http.js'

export function getTodayRecommendation() {
  return apiRequest('/api/recommendations/today')
}

export function refreshRecommendation() {
  return apiRequest('/api/recommendations/refresh', {
    method: 'POST',
  })
}

export function listRecommendationHistory(limit = 30) {
  return apiRequest(`/api/me/recommendations?limit=${limit}`)
}

export function submitFeedback(itemId, feedbackType, comment = '') {
  return apiRequest(`/api/recommendations/items/${itemId}/feedback`, {
    method: 'POST',
    body: { feedback_type: feedbackType, comment },
  })
}
