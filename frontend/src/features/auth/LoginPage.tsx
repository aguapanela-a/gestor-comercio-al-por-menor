import { ArrowRight, LockKeyhole, Store } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../auth/AuthProvider'

export function LoginPage() {
  const { token, login } = useAuth()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(location.state?.expired ? 'La sesión expiró. Vuelve a ingresar.' : '')
  const [loading, setLoading] = useState(false)

  if (token) return <Navigate to="/" replace />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username.trim(), password)
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'No fue posible iniciar sesión.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-layout">
      <section className="login-panel">
        <div className="login-brand">
          <div className="brand-mark"><Store size={21} /></div>
          <span>Mercantil <small>GESTIÓN COMERCIAL</small></span>
        </div>
        <div className="login-content">
          <span className="eyebrow">Acceso de colaboradores</span>
          <h1>Bienvenido de nuevo</h1>
          <p>Ingresa con tu usuario de la plataforma para continuar.</p>
          <form className="login-form" onSubmit={submit}>
            {error && <div className="login-error" role="alert">{error}</div>}
            <label className="form-field">
              <span>Nombre de usuario</span>
              <input
                autoComplete="username"
                required
                maxLength={50}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoFocus
              />
            </label>
            <label className="form-field">
              <span>Contraseña</span>
              <div className="password-input">
                <LockKeyhole size={17} />
                <input
                  type="password"
                  autoComplete="current-password"
                  required
                  maxLength={128}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>
            </label>
            <button type="submit" className="button button-primary login-submit" disabled={loading}>
              {loading ? 'Validando acceso…' : 'Iniciar sesión'}
              {!loading && <ArrowRight size={17} />}
            </button>
          </form>
        </div>
        <div className="login-footer">Acceso protegido · Gestor de Comercio al por Menor</div>
      </section>
      <aside className="login-aside">
        <div className="login-aside-copy">
          <span>OPERACIÓN CONECTADA</span>
          <h2>Una visión clara para cada área del negocio.</h2>
          <p>Administra catálogo, abastecimiento, inventarios y ventas desde un solo espacio de trabajo.</p>
        </div>
        <div className="login-aside-foot">Sistema de gestión comercial</div>
      </aside>
    </main>
  )
}
