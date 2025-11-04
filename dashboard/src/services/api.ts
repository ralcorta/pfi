import { getToken } from './auth'
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return fetch(url, {
    ...options,
    headers,
  })
}
export default {
  detections: () => `${apiBaseUrl}/detections`,
  login: () => `${apiBaseUrl}/v1/auth/login`,
  currentUser: () => `${apiBaseUrl}/v1/auth/me`,
}
export { fetchWithAuth }