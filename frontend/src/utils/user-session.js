const USER_ID_KEY = 'dailyFruit.userId'

export function getUserId() {
  const storedValue = window.localStorage.getItem(USER_ID_KEY)

  if (!storedValue || !/^\d+$/.test(storedValue)) {
    window.localStorage.removeItem(USER_ID_KEY)
    return null
  }

  const userId = Number(storedValue)

  if (!Number.isSafeInteger(userId) || userId <= 0) {
    window.localStorage.removeItem(USER_ID_KEY)
    return null
  }

  return userId
}

export function setUserId(userId) {
  if (!Number.isSafeInteger(userId) || userId <= 0) {
    throw new TypeError('userId must be a positive safe integer')
  }

  window.localStorage.setItem(USER_ID_KEY, String(userId))
}

export function clearUserId() {
  window.localStorage.removeItem(USER_ID_KEY)
}

export { USER_ID_KEY }
