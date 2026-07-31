import { apiRequest } from './http.js'

export function createUser(payload) {
  return apiRequest('/api/me', { method: 'POST', body: payload })
}

export function getUser() {
  return apiRequest('/api/me')
}

export function updateUser(payload) {
  return apiRequest('/api/me', { method: 'PUT', body: payload })
}

export function getFruitPreferences() {
  return apiRequest('/api/me/fruit-preferences')
}

export function replaceFruitPreferences(preferences) {
  return apiRequest('/api/me/fruit-preferences', {
    method: 'PUT',
    body: { preferences },
  })
}
