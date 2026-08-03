// Product feedback requests use the shared HTTP client for auth, timeout,
// JSON parsing, safe error mapping, and 401 handling.
import { apiRequest } from './http.js'

export function createProductFeedback(payload) {
  return apiRequest('/api/product-feedback', {
    method: 'POST',
    body: payload,
  })
}
