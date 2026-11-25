import { AlertCircle, LoaderCircle, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { PageHeader } from '../../components/common/PageHeader'
import { api, errorMessage } from '../../lib/api'

type AuditEntry = {
  id_auditoria: number
  id_usuario: number | null
  fecha_hora: string
  accion: string | null
  objeto_consultado: string | null
}

const PAGE_SIZE = 50

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
  const [entriesByOffset, setEntriesByOffset] = useState<Record<number, AuditEntry[]>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const entries = entriesByOffset[offset] ?? []
  const visibleEntries = entries.slice(0, PAGE_SIZE)
  const hasNext = entries.length > PAGE_SIZE

  useEffect(() => {
    const controller = new AbortController()

    async function loadAudit() {
      try {
        const { data } = await api.identidad.get<unknown>('/auth/audit', {
          params: { limit: PAGE_SIZE + 1, offset },
          signal: controller.signal,
        })
        if (!Array.isArray(data) || !data.every(isAuditEntry)) {
          throw new Error('El servicio devolvió registros de auditoría inválidos.')
        }
        if (!controller.signal.aborted) {
          setEntriesByOffset((previous) => ({ ...previous, [offset]: data }))
        }
      } catch (err) {
        if (!controller.signal.aborted) setError(errorMessage(err))
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }

    void loadAudit()
    return () => controller.abort()
  }, [offset, retry])

  function refresh() {
    setLoading(true)
    setError(null)
    setRetry((current) => current + 1)
  }

  function changePage(nextOffset: number) {
    setOffset(nextOffset)
    setLoading(true)
    setError(null)
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
                <th>ID usuario</th>
                <th>Fecha y hora</th>
                <th>Acción</th>
                <th>Objeto consultado</th>
              </tr>
            </thead>
            <tbody>
              {loading && visibleEntries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="table-state">
                    <LoaderCircle size={17} className="spin" />
                    Cargando auditorías...
                  </td>
                </tr>
              ) : error && visibleEntries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="table-state">
                    No fue posible cargar los registros.
                  </td>
                </tr>
              ) : visibleEntries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="table-state">
                    No hay registros de auditoría disponibles.
                  </td>
                </tr>
              ) : (
                visibleEntries.map((entry) => (
                  <tr key={entry.id_auditoria}>
                    <td>{String(entry.id_auditoria)}</td>
                    <td>{entry.id_usuario ?? '—'}</td>
                    <td>{new Date(entry.fecha_hora).toLocaleString('es-CO')}</td>
                    <td>{entry.accion ?? '—'}</td>
                    <td>{entry.objeto_consultado ?? '—'}</td>
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
