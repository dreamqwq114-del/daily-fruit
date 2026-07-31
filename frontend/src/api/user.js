import { apiRequest } from './http.js'

export function createUser(payload) {
  return apiRequest('/api/users', { method: 'POST', body: payload })
}

export function getUser(userId) {
  return apiRequest(`/api/users/${userId}`)
}

export function updateUser(userId, payload) {
  return apiRequest(`/api/users/${userId}`, { method: 'PUT', body: payload })
}

export function getFruitPreferences(userId) {
  return apiRequest(`/api/users/${userId}/fruit-preferences`)
}

export function replaceFruitPreferences(userId, preferences) {
  return apiRequest(`/api/users/${userId}/fruit-preferences`, {
    method: 'PUT',
    body: { preferences },
  })
}
