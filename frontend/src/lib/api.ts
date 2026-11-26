import axios, { AxiosError, type AxiosInstance } from 'axios'

export type ServiceName =
  | 'identidad'
  | 'catalogo'
  | 'organizacion'
  | 'compras'
  | 'inventarios'
  | 'ventas'
  | 'reportes'

function configuredUrl(value: string | undefined, fallback: string): string {
  return value?.trim() || fallback
}

const serviceUrls: Record<ServiceName, string> = {
  identidad: configuredUrl(import.meta.env.VITE_IDENTIDAD_API_URL, 'http://127.0.0.1:8001'),
  catalogo: configuredUrl(import.meta.env.VITE_CATALOGO_API_URL, 'http://127.0.0.1:8002'),
  organizacion: configuredUrl(import.meta.env.VITE_ORGANIZACION_API_URL, 'http://127.0.0.1:8003'),
  compras: configuredUrl(import.meta.env.VITE_COMPRAS_API_URL, 'http://127.0.0.1:8004'),
  inventarios: configuredUrl(import.meta.env.VITE_INVENTARIOS_API_URL, 'http://127.0.0.1:8005'),
  ventas: configuredUrl(import.meta.env.VITE_VENTAS_API_URL, 'http://127.0.0.1:8006'),
  reportes: configuredUrl(import.meta.env.VITE_REPORTES_API_URL, 'http://127.0.0.1:8007'),
}

const clientUrls: Record<ServiceName, string> = import.meta.env.DEV
  ? {
      identidad: '/api/identidad',
      catalogo: '/api/catalogo',
      organizacion: '/api/organizacion',
      compras: '/api/compras',
      inventarios: '/api/inventarios',
      ventas: '/api/ventas',
      reportes: '/api/reportes',
    }
  : serviceUrls

export const TOKEN_KEY = 'retail.access-token'
export const USER_KEY = 'retail.user'

const clients = Object.fromEntries(
  Object.entries(clientUrls).map(([name, baseURL]) => [
    name,
    axios.create({ baseURL, timeout: 8000 }),
  ]),
) as Record<ServiceName, AxiosInstance>

Object.values(clients).forEach((client) => {
  client.interceptors.request.use((config) => {
    const token = sessionStorage.getItem(TOKEN_KEY)
    if (token) config.headers.Authorization = `Bearer ${token}`
    if (!config.headers['X-Correlation-ID']) {
      config.headers['X-Correlation-ID'] = globalThis.crypto?.randomUUID
        ? globalThis.crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(16).slice(2)}`
    }
    return config
  })
  client.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      if (error.response?.status === 401 && !error.config?.url?.endsWith('/auth/login')) {
        sessionStorage.removeItem(TOKEN_KEY)
        sessionStorage.removeItem(USER_KEY)
        window.dispatchEvent(new Event('retail:session-expired'))
      }
      return Promise.reject(error)
    },
  )
})

export const api = clients
export const serviceUrl = (service: ServiceName) => serviceUrls[service]


export function errorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : 'Ocurrió un error inesperado.'
  }

  const status = error.response?.status
  const data = error.response?.data
  const detail = data?.detail

  // La operación quedó confirmada, pero falló la entrega de auditoría.
  const committed =
    data?.business_operation_committed === true ||
    detail?.business_operation_committed === true

  if (status === 503 && committed) {
    return 'La operación fue realizada y guardada correctamente, pero no se pudo registrar su auditoría. No la repitas. Contacta al administrador para revisar el registro.'
  }

  if (Array.isArray(detail)) {
    return detail.map((item: { msg?: string; loc?: string[] }) =>
      `${item.loc?.slice(-1)[0] ?? 'Campo'}: ${item.msg ?? 'valor inválido'}`,
    ).join(' · ')
  }

  if (typeof detail === 'string') {
    if (status === 404) return `No se encontró el recurso. ${detail}`
    if (status === 409) return `Conflicto: ${detail}`
    if (status === 422) return `Revisa los datos: ${detail}`
    return detail
  }

  if (status === 401) return 'La sesión terminó. Inicia sesión nuevamente.'
  if (status === 403) return 'Tu cuenta no está activa o no tiene acceso.'
  if (status === 404) return 'No se encontró el recurso solicitado.'
  if (status === 409) return 'La operación entra en conflicto con el estado actual.'
  if (status === 422) return 'Hay campos inválidos. Revisa la información ingresada.'
  if (status === 503) return 'El servicio no está disponible temporalmente. Comprueba el estado de la operación antes de repetirla.'
  if (status && status >= 500) return 'El servicio presentó un error. Intenta más tarde.'
  if (!error.response) return 'No fue posible conectar con el servicio. Verifica que esté disponible.'

  return 'No se pudo completar la solicitud.'
}
