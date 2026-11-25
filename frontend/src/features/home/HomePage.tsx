import {
  ArrowUpRight,
  Boxes,
  Building2,
  CircleCheck,
  CircleX,
  LoaderCircle,
  Package,
  ShoppingCart,
  Users,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/AuthProvider'
import { api, serviceUrl, type ServiceName } from '../../lib/api'
import { PageHeader } from '../../components/common/PageHeader'

const serviceList: { key: ServiceName; name: string }[] = [
  { key: 'identidad', name: 'Identidad' },
  { key: 'catalogo', name: 'Catálogo' },
  { key: 'organizacion', name: 'Organización' },
  { key: 'compras', name: 'Compras' },
  { key: 'inventarios', name: 'Inventarios' },
  { key: 'ventas', name: 'Ventas' },
]

const shortcuts = [
  { label: 'Consultar productos', detail: 'Catálogo y precios', to: '/catalog/products', icon: Package },
  { label: 'Revisar existencias', detail: 'Disponibilidad por almacén', to: '/inventory/stock', icon: Boxes },
  { label: 'Crear pedido', detail: 'Registrar una venta', to: '/sales/orders', icon: ShoppingCart },
  { label: 'Directorio de equipo', detail: 'Empleados y usuarios', to: '/identity/employees', icon: Users },
]

function getServiceHost(url: string | undefined): string {
  if (!url?.trim()) return 'URL no configurada'
  try {
    const host = new URL(url.trim()).host
    return host || 'URL no configurada'
  } catch {
    return 'URL no configurada'
  }
}

export function HomePage() {
  const { user } = useAuth()
  const [health, setHealth] = useState<Record<string, 'checking' | 'online' | 'offline'>>({})

  useEffect(() => {
    let active = true
    serviceList.forEach(async ({ key }) => {
      try {
        const { data } = await api[key].get<{ status?: string }>('/health', { timeout: 3500 })
        if (active) setHealth((current) => ({ ...current, [key]: data.status === 'running' ? 'online' : 'offline' }))
      } catch {
        if (active) setHealth((current) => ({ ...current, [key]: 'offline' }))
      }
    })
    return () => { active = false }
  }, [])

  return (
    <>
      <PageHeader eyebrow="Panel de trabajo" title={`Hola, ${user?.nombre_completo?.split(' ')[0] ?? 'bienvenido'}`} description="Accede a las herramientas operativas de tu organización." />
      <section className="home-intro">
        <div className="intro-copy">
          <span className="eyebrow">GESTIÓN COMERCIAL</span>
          <h2>La operación, en orden.</h2>
          <p>Consulta la información disponible y continúa con las tareas de tu equipo.</p>
        </div>
        <div className="intro-mark"><Building2 size={54} strokeWidth={1.2} /></div>
      </section>
      <section className="home-section">
        <div className="section-heading">
          <div><h2>Accesos rápidos</h2><p>Atajos a tareas frecuentes</p></div>
        </div>
        <div className="shortcut-grid">
          {shortcuts.map(({ label, detail, to, icon: Icon }) => (
            <Link className="shortcut-link" to={to} key={to}>
              <div className="shortcut-icon"><Icon size={19} /></div>
              <div><strong>{label}</strong><span>{detail}</span></div>
              <ArrowUpRight size={17} className="shortcut-arrow" />
            </Link>
          ))}
        </div>
      </section>
      <section className="home-section">
        <div className="section-heading">
          <div><h2>Conexión de servicios</h2><p>Estado consultado en tiempo real; los servicios pueden estar fuera de línea.</p></div>
        </div>
        <div className="service-list">
          {serviceList.map(({ key, name }) => {
            const state = health[key] ?? 'checking'
            const StateIcon = state === 'checking' ? LoaderCircle : state === 'online' ? CircleCheck : CircleX
            return (
              <div className="service-row" key={key}>
                <div className="service-indicator"><StateIcon size={17} className={state === 'checking' ? 'spin' : ''} /></div>
                <div><strong>{name}</strong><span>{getServiceHost(serviceUrl(key))}</span></div>
                <span className={`service-state service-${state}`}>{state === 'checking' ? 'Verificando' : state === 'online' ? 'Disponible' : 'Sin conexión'}</span>
              </div>
            )
          })}
          <div className="service-row service-future">
            <div className="service-indicator"><CircleX size={17} /></div>
            <div><strong>Reportes</strong><span>API pendiente de integración</span></div>
            <span className="service-state service-offline">No conectado</span>
          </div>
        </div>
      </section>
    </>
  )
}
