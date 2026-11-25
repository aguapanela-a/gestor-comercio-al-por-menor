import { LogOut, Menu, Store, X } from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { navigationGroups, routeTitles } from '../app/navigation'
import { useAuth } from '../auth/AuthProvider'

export function PrivateLayout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const pageTitle = routeTitles.get(location.pathname) ?? 'Inicio'

  return (
    <div className="app-shell">
      {sidebarOpen && <button className="mobile-backdrop" aria-label="Cerrar menú" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><Store size={20} /></div>
          <div><strong>Mercantil</strong><small>Gestión comercial</small></div>
          <button type="button" className="icon-button sidebar-close" aria-label="Cerrar menú" onClick={() => setSidebarOpen(false)}><X size={18} /></button>
        </div>
        <nav className="side-nav" aria-label="Navegación principal">
          {navigationGroups.map((group) => (
            <section className="nav-group" key={group.label}>
              <span className="nav-heading">{group.label}</span>
              {group.items.map(({ label, path, icon: Icon }) => (
                <NavLink
                  key={path}
                  to={path}
                  end={path === '/'}
                  className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
                  onClick={() => setSidebarOpen(false)}
                >
                  <Icon size={17} strokeWidth={1.8} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </section>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="connection-dot" />
          <span>Sesión autenticada</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button type="button" className="icon-button mobile-menu" aria-label="Abrir menú" onClick={() => setSidebarOpen(true)}>
            <Menu size={20} />
          </button>
          <div className="topbar-title">{pageTitle}</div>
          <div className="user-menu">
            <div className="user-avatar" aria-hidden="true">{user?.nombre_completo?.charAt(0).toUpperCase() ?? 'U'}</div>
            <div className="user-meta">
              <strong>{user?.nombre_completo ?? 'Usuario'}</strong>
              <span>{user?.nombre_usuario ?? ''}</span>
            </div>
            <button type="button" className="button button-quiet button-small logout-button" onClick={logout}>
              <LogOut size={16} /><span>Salir</span>
            </button>
          </div>
        </header>
        <main className="workspace"><Outlet /></main>
      </div>
    </div>
  )
}
