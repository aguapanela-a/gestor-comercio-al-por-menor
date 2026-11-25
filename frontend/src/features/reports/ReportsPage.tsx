import { AlertCircle, CheckCircle2, Clock3, LoaderCircle, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, errorMessage } from '../../lib/api'
import { PageHeader } from '../../components/common/PageHeader'

type Row = Record<string, unknown>

const reports = [
  { id: 'vista_inventario_por_sede', name: 'Inventario por sede', description: 'Existencias agrupadas por sede.', ready: true },
  { id: 'vista_alertas_reabastecimiento', name: 'Alertas de reabastecimiento', description: 'Productos que requieren reposición.', ready: true },
  { id: 'vista_productos_sin_inventario', name: 'Productos sin inventario', description: 'Productos registrados sin existencias.', ready: true },
  { id: 'vista_ventas_mensuales_por_sede', name: 'Ventas mensuales por sede', description: 'Resumen mensual de ventas.', ready: false },
  { id: 'vista_pedidos_pendientes', name: 'Pedidos pendientes', description: 'Pedidos pendientes de atención.', ready: false },
  { id: 'vista_saldos_pendientes', name: 'Saldos pendientes', description: 'Saldos pendientes de pago.', ready: false },
  { id: 'vista_compras_pendientes', name: 'Compras pendientes', description: 'Órdenes y cantidades pendientes de recibir.', ready: true },
  { id: 'vista_transferencias_en_transito', name: 'Transferencias en tránsito', description: 'Movimientos entre almacenes.', ready: true },
  { id: 'vista_devoluciones_por_producto', name: 'Devoluciones por producto', description: 'Resumen de devoluciones.', ready: false },
  { id: 'vista_reporte_corporativo', name: 'Reporte corporativo', description: 'Indicadores consolidados del negocio.', ready: false },
] as const

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'Sí' : 'No'
  if (typeof value === 'object') return JSON.stringify(value)
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
    return new Date(value).toLocaleString('es-CO')
  }
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return new Date(`${value}T12:00:00`).toLocaleDateString('es-CO')
  }
  return String(value)
}

function columnLabel(value: string): string {
  return value
    .replace(/^id_/, 'ID ')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function ReportsPage() {
  const [selected, setSelected] = useState<string>('vista_productos_sin_inventario')
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const limit = 20

  const current = reports.find((report) => report.id === selected)!

  const load = useCallback(async () => {
    if (!current.ready) {
      setRows([])
      setError(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const { data } = await api.reportes.get<unknown>(`/${selected}`)
      setRows(Array.isArray(data) ? data as Row[] : [])
      setPage(0)
    } catch (err) {
      setRows([])
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [current.ready, selected])

  useEffect(() => {
    void load()
  }, [load])

  const columns = useMemo(
    () => rows.length ? Object.keys(rows[0]) : [],
    [rows],
  )

  const visibleRows = rows.slice(page * limit, (page + 1) * limit)
  const totalPages = Math.max(1, Math.ceil(rows.length / limit))

  return (
    <>
      <PageHeader
        eyebrow="Análisis"
        title="Reportes"
        description="Consulta información consolidada de las diferentes áreas del comercio."
        action={
          <button
            type="button"
            className="button button-outline"
            onClick={() => void load()}
            disabled={loading || !current.ready}
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            Actualizar
          </button>
        }
      />

      <section className="home-section">
        <div className="section-heading">
          <div>
            <h2>Reportes disponibles</h2>
            <p>Selecciona un reporte para consultar su información.</p>
          </div>
        </div>

        <div className="report-selector">
          {reports.map((report) => (
            <button
              type="button"
              key={report.id}
              className={`report-option ${selected === report.id ? 'report-option-active' : ''}`}
              onClick={() => {
                setSelected(report.id)
                setPage(0)
              }}
            >
              <span className="report-option-title">{report.name}</span>
              <span className="report-option-status">
                {report.ready
                  ? <><CheckCircle2 size={13} /> Conectado</>
                  : <><Clock3 size={13} /> En desarrollo</>}
              </span>
            </button>
          ))}
        </div>
      </section>

      <section className="home-section">
        <div className="section-heading">
          <div>
            <h2>{current.name}</h2>
            <p>{current.description}</p>
          </div>
          {current.ready && !loading && !error && (
            <span className="report-count">{rows.length} registros</span>
          )}
        </div>

        {!current.ready && (
          <div className="empty-feature report-empty">
            <div className="empty-feature-mark"><Clock3 size={23} /></div>
            <h2>Reporte en desarrollo</h2>
            <p>Este reporte todavía no está implementado en el servicio. Estará disponible cuando se complete su consulta en la API.</p>
          </div>
        )}

        {current.ready && error && (
          <div className="notice notice-error">
            <AlertCircle size={17} />
            <span>{error}</span>
            <button type="button" onClick={() => void load()}>Reintentar</button>
          </div>
        )}

        {current.ready && (
          <div className="table-card">
            <div className="table-scroll">
              <table>
                {columns.length > 0 && (
                  <thead>
                    <tr>
                      {columns.map((column) => (
                        <th key={column}>{columnLabel(column)}</th>
                      ))}
                    </tr>
                  </thead>
                )}
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={Math.max(columns.length, 1)} className="table-state">
                        <LoaderCircle size={17} className="spin" />
                        Cargando reporte...
                      </td>
                    </tr>
                  ) : error ? (
                    <tr>
                      <td colSpan={Math.max(columns.length, 1)} className="table-state">
                        No fue posible cargar la información.
                      </td>
                    </tr>
                  ) : rows.length === 0 ? (
                    <tr>
                      <td colSpan={Math.max(columns.length, 1)} className="table-state">
                        No hay registros disponibles para este reporte.
                      </td>
                    </tr>
                  ) : (
                    visibleRows.map((row, index) => (
                      <tr key={index}>
                        {columns.map((column) => (
                          <td key={column}>{formatValue(row[column])}</td>
                        ))}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {!loading && !error && rows.length > 0 && (
              <div className="table-footer">
                <span>
                  Mostrando {page * limit + 1}–{Math.min((page + 1) * limit, rows.length)} de {rows.length} registros
                </span>
                <div className="pagination">
                  <button
                    type="button"
                    className="button button-outline button-small"
                    disabled={page === 0}
                    onClick={() => setPage((value) => Math.max(0, value - 1))}
                  >
                    Anterior
                  </button>
                  <button
                    type="button"
                    className="button button-outline button-small"
                    disabled={page + 1 >= totalPages}
                    onClick={() => setPage((value) => Math.min(totalPages - 1, value + 1))}
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </>
  )
}
