import { AlertCircle, LoaderCircle, RefreshCw, Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { PageHeader } from '../../components/common/PageHeader'
import { api, errorMessage } from '../../lib/api'

type AuditEntry = {
  id_auditoria: number
  id_usuario: number | null
  fecha_hora: string
  accion: string | null
  objeto_consultado: string | null
  event_id?: string | null
  microservicio?: string
  modulo?: string
  tipo_objeto?: string | null
  id_objeto?: string | null
  resultado?: 'SUCCESS' | 'FAILURE' | 'DENIED'
  metodo_http?: string | null
  ruta?: string | null
  direccion_ip?: string | null
  correlation_id?: string | null
  detalles?: Record<string, unknown>
  nombre_usuario?: string | null
  nombre_completo?: string | null
}

const PAGE_SIZE = 50
const SERVICES = ['identidad', 'catalogo', 'organizacion', 'compras', 'inventarios', 'reportes', 'ventas']
const RESULTS = ['SUCCESS', 'FAILURE', 'DENIED'] as const

type AuditFilters = {
  text: string
  service: string
  module: string
  result: string
  action: string
  userId: string
  from: string
  to: string
}

const EMPTY_FILTERS: AuditFilters = {
  text: '',
  service: '',
  module: '',
  result: '',
  action: '',
  userId: '',
  from: '',
  to: '',
}

function requestParams(filters: AuditFilters, offset: number) {
  const params: Record<string, string | number> = {
    limit: PAGE_SIZE + 1,
    offset,
  }
  if (filters.text.trim()) params.texto = filters.text.trim()
  if (filters.service) params.microservicio = filters.service
  if (filters.module.trim()) params.modulo = filters.module.trim()
  if (filters.result) params.resultado = filters.result
  if (filters.action.trim()) params.accion = filters.action.trim()
  if (filters.userId) params.id_usuario = Number(filters.userId)
  if (filters.from) params.fecha_desde = new Date(filters.from).toISOString()
  if (filters.to) params.fecha_hasta = new Date(filters.to).toISOString()
  return params
}

function isAuditEntry(value: unknown): value is AuditEntry {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false
  const entry = value as Record<string, unknown>
  return typeof entry.id_auditoria === 'number'
    && (typeof entry.id_usuario === 'number' || entry.id_usuario === null)
    && typeof entry.fecha_hora === 'string'
    && (typeof entry.accion === 'string' || entry.accion === null)
    && (typeof entry.objeto_consultado === 'string' || entry.objeto_consultado === null)
}

export function AuditPage() {
  const [offset, setOffset] = useState(0)
  const [retry, setRetry] = useState(0)
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [entriesByOffset, setEntriesByOffset] = useState<Record<number, AuditEntry[]>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const loadingRef = useRef(false)
  const entries = entriesByOffset[offset] ?? []
  const visibleEntries = entries.slice(0, PAGE_SIZE)
  const hasNext = entries.length > PAGE_SIZE

  useEffect(() => {
    const controller = new AbortController()

    async function loadAudit() {
      if (loadingRef.current) return
      loadingRef.current = true
      try {
        const { data, headers } = await api.identidad.get<unknown>('/auth/audit', {
          params: requestParams(appliedFilters, offset),
          signal: controller.signal,
        })
        if (!Array.isArray(data) || !data.every(isAuditEntry)) {
          throw new Error('El servicio devolvió registros de auditoría inválidos.')
        }
        if (!controller.signal.aborted) {
          setEntriesByOffset((previous) => ({ ...previous, [offset]: data }))
          setError(
            headers?.['x-audit-status'] === 'failed'
              ? 'Los registros se consultaron, pero no fue posible registrar esta consulta en auditoría.'
              : null,
          )
        }
      } catch (err) {
        if (!controller.signal.aborted) setError(errorMessage(err))
      } finally {
        if (!controller.signal.aborted) {
          loadingRef.current = false
          setLoading(false)
        }
      }
    }

    void loadAudit()
    return () => {
      controller.abort()
      loadingRef.current = false
    }
  }, [appliedFilters, offset, retry])

  useEffect(() => {
    const interval = window.setInterval(() => {
      if (!loadingRef.current) {
        setError(null)
        setRetry((current) => current + 1)
      }
    }, 30_000)
    return () => window.clearInterval(interval)
  }, [])

  function refresh() {
    if (loadingRef.current) return
    setLoading(true)
    setError(null)
    setRetry((current) => current + 1)
  }

  function changePage(nextOffset: number) {
    setOffset(nextOffset)
    setLoading(true)
    setError(null)
  }

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setOffset(0)
    setEntriesByOffset({})
    setError(null)
    setLoading(true)
    setAppliedFilters({ ...filters })
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS)
    setOffset(0)
    setEntriesByOffset({})
    setError(null)
    setLoading(true)
    setAppliedFilters(EMPTY_FILTERS)
    setRetry((current) => current + 1)
  }

  function updateFilter(field: keyof AuditFilters, value: string) {
    setFilters((current) => ({ ...current, [field]: value }))
  }

  return (
    <>
      <PageHeader
        eyebrow="Identidad"
        title="Auditorías"
        description="Consulta los accesos y operaciones registrados."
        action={
          <button
            type="button"
            className="button button-outline"
            onClick={refresh}
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            Actualizar
          </button>
        }
      />

      <form className="filter-bar filter-form" onSubmit={applyFilters}>
        <label className="search-field">
          <Search size={16} aria-hidden="true" />
          <input
            aria-label="Buscar en auditoría"
            placeholder="Buscar acción, objeto o ruta"
            value={filters.text}
            onChange={(event) => updateFilter('text', event.target.value)}
          />
        </label>
        <label className="form-field">
          <span>Servicio</span>
          <select
            aria-label="Filtrar por servicio"
            value={filters.service}
            onChange={(event) => updateFilter('service', event.target.value)}
          >
            <option value="">Todos los servicios</option>
            {SERVICES.map((service) => <option key={service} value={service}>{service}</option>)}
          </select>
        </label>
        <label className="form-field">
          <span>Resultado</span>
          <select
            aria-label="Filtrar por resultado"
            value={filters.result}
            onChange={(event) => updateFilter('result', event.target.value)}
          >
            <option value="">Todos los resultados</option>
            {RESULTS.map((result) => <option key={result} value={result}>{result}</option>)}
          </select>
        </label>
        <input
          aria-label="Filtrar por módulo"
          className="audit-filter-input"
          placeholder="Módulo"
          value={filters.module}
          onChange={(event) => updateFilter('module', event.target.value)}
        />
        <input
          aria-label="Filtrar por acción"
          className="audit-filter-input"
          placeholder="Acción"
          value={filters.action}
          onChange={(event) => updateFilter('action', event.target.value)}
        />
        <input
          aria-label="Filtrar por ID de usuario"
          className="audit-filter-input"
          type="number"
          min="1"
          placeholder="ID usuario"
          value={filters.userId}
          onChange={(event) => updateFilter('userId', event.target.value)}
        />
        <label className="form-field audit-date-field">
          <span>Desde</span>
          <input
            aria-label="Fecha desde"
            type="datetime-local"
            value={filters.from}
            onChange={(event) => updateFilter('from', event.target.value)}
          />
        </label>
        <label className="form-field audit-date-field">
          <span>Hasta</span>
          <input
            aria-label="Fecha hasta"
            type="datetime-local"
            value={filters.to}
            onChange={(event) => updateFilter('to', event.target.value)}
          />
        </label>
        <button type="submit" className="button button-primary button-small" disabled={loading}>
          Filtrar
        </button>
        <button type="button" className="button button-outline button-small" onClick={clearFilters}>
          Limpiar
        </button>
      </form>

      {error && (
        <div className="notice notice-error">
          <AlertCircle size={17} />
          <span>{error}</span>
          <button type="button" onClick={refresh}>Reintentar</button>
        </div>
      )}

      <section className="table-card">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>ID auditoría</th>
                <th>Usuario</th>
                <th>Fecha y hora</th>
                <th>Servicio</th>
                <th>Módulo</th>
                <th>Resultado</th>
                <th>Acción</th>
                <th>Objeto</th>
                <th>Detalles</th>
              </tr>
            </thead>
            <tbody>
              {loading && visibleEntries.length === 0 ? (
                <tr>
                  <td colSpan={9} className="table-state">
                    <LoaderCircle size={17} className="spin" />
                    Cargando auditorías...
                  </td>
                </tr>
              ) : error && visibleEntries.length === 0 ? (
                <tr>
                  <td colSpan={9} className="table-state">
                    No fue posible cargar los registros.
                  </td>
                </tr>
              ) : visibleEntries.length === 0 ? (
                <tr>
                  <td colSpan={9} className="table-state">
                    No hay registros de auditoría disponibles.
                  </td>
                </tr>
              ) : (
                visibleEntries.map((entry) => (
                  <tr key={entry.id_auditoria}>
                    <td>{String(entry.id_auditoria)}</td>
                    <td>{entry.nombre_completo ?? entry.nombre_usuario ?? entry.id_usuario ?? '—'}</td>
                    <td>{new Date(entry.fecha_hora).toLocaleString('es-CO')}</td>
                    <td>{entry.microservicio ?? 'identidad'}</td>
                    <td>{entry.modulo ?? '—'}</td>
                    <td>{entry.resultado ?? 'SUCCESS'}</td>
                    <td>{entry.accion ?? '—'}</td>
                    <td>
                      {entry.tipo_objeto ?? entry.objeto_consultado ?? '—'}
                      {entry.id_objeto && <small className="audit-object-id">ID: {entry.id_objeto}</small>}
                      {entry.ruta && <small className="audit-object-id">{entry.ruta}</small>}
                    </td>
                    <td>
                      {entry.detalles && Object.keys(entry.detalles).length > 0 ? (
                        <details>
                          <summary>Ver detalles</summary>
                          <pre className="audit-details">{JSON.stringify(entry.detalles, null, 2)}</pre>
                        </details>
                      ) : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {(offset > 0 || hasNext) && (
          <div className="table-footer">
            <span>
              Página {Math.floor(offset / PAGE_SIZE) + 1}
              {visibleEntries.length > 0 && ` · ${visibleEntries.length} registros`}
            </span>
            <div className="pagination">
              <button
                type="button"
                className="button button-outline button-small"
                disabled={offset === 0 || loading}
                onClick={() => changePage(Math.max(0, offset - PAGE_SIZE))}
              >
                Anterior
              </button>
              <button
                type="button"
                className="button button-outline button-small"
                disabled={!hasNext || loading}
                onClick={() => changePage(offset + PAGE_SIZE)}
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </section>
    </>
  )
}
