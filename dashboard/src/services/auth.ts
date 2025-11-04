const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'
const TOKEN_KEY = 'auth_token'
const VNI_KEY = 'user_vni'
export interface LoginResponse {
  access_token: string
  token_type: string
  email: string
  vni_cliente: number
}
export interface LoginRequest {
  email: string
  password: string
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}
export function isAuthenticated(): boolean {
  return getToken() !== null
}
export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Error de autenticación' }))
    throw new Error(error.detail || 'Email o contraseña incorrectos')
  }
  const data: LoginResponse = await response.json()
  setToken(data.access_token)
  localStorage.setItem(VNI_KEY, data.vni_cliente.toString())
  return data
}
export function logout(): void {
  removeToken()
  localStorage.removeItem(VNI_KEY)
}
export function getUserVni(): number | null {
  const vni = localStorage.getItem(VNI_KEY)
  return vni ? parseInt(vni, 10) : null
}
export function getAuthHeader(): { Authorization: string } | Record<string, never> {
  const token = getToken()
  if (token) {
    return { Authorization: `Bearer ${token}` }
  }
  return {}
}