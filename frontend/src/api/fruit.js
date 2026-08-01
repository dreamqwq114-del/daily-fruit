// 水果目录只读 API；请求仍需 Supabase access token，由 http.js 统一附加。
import { apiRequest } from './http.js'

export function listFruits() {
  // GET /api/fruits 供建档、偏好页加载可选择的 active 水果。
  return apiRequest('/api/fruits')
}

export function getFruit(fruitId) {
  // GET /api/fruits/:id 读取单个详情，当前页面主要使用 listFruits。
  return apiRequest(`/api/fruits/${fruitId}`)
}
