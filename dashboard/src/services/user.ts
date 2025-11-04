import { fetchWithAuth } from './api'
import api from './api'
export interface CurrentUser {
  email: string
  vni_cliente: number
  traffic_mirror_target_id: string
  created_at: number
}
export async function getCurrentUser(): Promise<CurrentUser> {
  const response = await fetchWithAuth(api.currentUser())
  if (!response.ok) {
    if (response.status === 401) {
      const { logout } = await import('./auth')
      logout()
      window.location.href = '/auth/login'
      throw new Error('Sesión expirada. Por favor, inicia sesión nuevamente.')
    }
    const error = await response.json().catch(() => ({ detail: 'Error al obtener información del usuario' }))
    throw new Error(error.detail || 'Error al obtener información del usuario')
  }
  const data: CurrentUser = await response.json()
  return data
}