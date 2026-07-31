import { apiRequest } from './http.js'

export function listFruits() {
  return apiRequest('/api/fruits')
}

export function getFruit(fruitId) {
  return apiRequest(`/api/fruits/${fruitId}`)
}
