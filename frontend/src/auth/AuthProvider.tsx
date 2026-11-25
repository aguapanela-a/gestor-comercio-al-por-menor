import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { api, errorMessage, TOKEN_KEY, USER_KEY } from '../lib/api'

export interface AuthUser {
  id_usuario: number
  id_empleado: number
  nombre_usuario: string
  nombre_completo: string
  cargo: string
  id_sede: number
}

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  ready: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readStoredUser(): AuthUser | null {
  try {
    const raw = sessionStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) as AuthUser : null
  } catch {
    sessionStorage.removeItem(USER_KEY)
    return null
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<AuthUser | null>(readStoredUser)
  const [ready, setReady] = useState(false)

  const logout = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
    navigate('/login', { replace: true })
  }, [navigate])

  useEffect(() => {
    const expire = () => {
      setToken(null)
      setUser(null)
      navigate('/login', { replace: true, state: { expired: true } })
    }
    window.addEventListener('retail:session-expired', expire)
    return () => window.removeEventListener('retail:session-expired', expire)
  }, [navigate])

  useEffect(() => {
    let active = true
    async function verify() {
      if (!token) {
        setReady(true)
        return
      }
      try {
        const { data } = await api.identidad.get<AuthUser & { correo: string | null }>('/auth/me')
        if (active) {
          setUser({
            id_usuario: data.id_usuario,
            id_empleado: data.id_empleado,
            nombre_usuario: data.nombre_usuario,
            nombre_completo: data.nombre_completo,
            cargo: data.cargo,
            id_sede: data.id_sede,
          })
          sessionStorage.setItem(USER_KEY, JSON.stringify(data))
        }
      } catch (error) {
        if (active && !sessionStorage.getItem(TOKEN_KEY)) {
          setToken(null)
          setUser(null)
        } else if (active && axios.isAxiosError(error) && [401, 403].includes(error.response?.status ?? 0)) {
          logout()
        }
      } finally {
        if (active) setReady(true)
      }
    }
    void verify()
    return () => { active = false }
  }, [token, logout])

  const login = useCallback(async (username: string, password: string) => {
    try {
      const { data } = await api.identidad.post<{ access_token: string; user: AuthUser }>(
        '/auth/login',
        { nombre_usuario: username, password },
      )
      sessionStorage.setItem(TOKEN_KEY, data.access_token)
      sessionStorage.setItem(USER_KEY, JSON.stringify(data.user))
      setToken(data.access_token)
      setUser(data.user)
      setReady(true)
    } catch (error) {
      throw new Error(errorMessage(error))
    }
  }, [])

  const value = useMemo(() => ({ user, token, ready, login, logout }), [user, token, ready, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return value
}
