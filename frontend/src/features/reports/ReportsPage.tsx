import { AlertCircle, CheckCircle2, LoaderCircle, RefreshCw, Search } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, errorMessage } from '../../lib/api'
import { PageHeader } from '../../components/common/PageHeader'

type Row = Record<string, unknown>
const EMPTY_ROWS: Row[] = []

type ReportColumn = {
  name: string
  type: string
  nullable: boolean
  description: string | null
}

type ReportView = {
  name: string
  schema: string
  label: string
  description: string | null
  columns: ReportColumn[]
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function isReportView(value: unknown): value is ReportView {
  return isRecord(value)
    && typeof value.name === 'string'
    && typeof value.schema === 'string'
    && typeof value.label === 'string'
    && (typeof value.description === 'string' || value.description === null)
    && Array.isArray(value.columns)
    && value.columns.every((column) =>
      isRecord(column)
      && typeof column.name === 'string'
      && typeof column.type === 'string'
      && typeof column.nullable === 'boolean'
      && (typeof column.description === 'string' || column.description === null),
    )
}

function parseReportViews(value: unknown): ReportView[] {
  if (!Array.isArray(value) || !value.every(isReportView)) {
    throw new Error('El servicio devolvió un catálogo de reportes inválido.')
  }
  return value
}

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
  const [reportViews, setReportViews] = useState<ReportView[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [rowsByView, setRowsByView] = useState<Record<string, Row[]>>({})
  const [lastUpdatedByView, setLastUpdatedByView] = useState<Record<string, number>>({})
  const [viewErrors, setViewErrors] = useState<Record<string, string>>({})
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [loadingView, setLoadingView] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const selectedRef = useRef(selected)
  selectedRef.current = selected
  const reportViewsRef = useRef(reportViews)
  reportViewsRef.current = reportViews
  const catalogRequestRef = useRef<{
    controller: AbortController
    promise: Promise<void>
  } | null>(null)
  const viewRequestRef = useRef<{
    viewName: string
    controller: AbortController
    promise: Promise<void>
  } | null>(null)
  const limit = 20

  const current = reportViews.find((view) => view.name === selected)
  const rows = selected ? rowsByView[selected] ?? EMPTY_ROWS : EMPTY_ROWS
  const loading = selected !== null && loadingView === selected
  const error = selected ? viewErrors[selected] ?? null : null

  const loadCatalog = useCallback(async () => {
    while (catalogRequestRef.current) {
      const activeRequest = catalogRequestRef.current
      if (!activeRequest.controller.signal.aborted) {
        await activeRequest.promise
        return
      }
      await activeRequest.promise
    }

    const controller = new AbortController()
    setCatalogLoading(true)
    setCatalogError(null)

    const promise = (async () => {
      try {
        const { data } = await api.reportes.get<unknown>('/vistas', {
          params: { _refresh: Date.now() },
          signal: controller.signal,
        })
        if (
          controller.signal.aborted
          || catalogRequestRef.current?.controller !== controller
        ) return

        const nextViews = parseReportViews(data)
        const availableNames = new Set(nextViews.map((view) => view.name))
        const currentSelection = selectedRef.current
        const nextSelection = currentSelection && availableNames.has(currentSelection)
          ? currentSelection
          : nextViews[0]?.name ?? null

        reportViewsRef.current = nextViews
        selectedRef.current = nextSelection
        setReportViews(nextViews)
        if (nextSelection !== currentSelection) {
          viewRequestRef.current?.controller.abort()
          setSelected(nextSelection)
          setPage(0)
        }
        setRowsByView((previous) => Object.fromEntries(
          Object.entries(previous).filter(([name]) => availableNames.has(name)),
        ))
        setLastUpdatedByView((previous) => Object.fromEntries(
          Object.entries(previous).filter(([name]) => availableNames.has(name)),
        ))
        setViewErrors((previous) => Object.fromEntries(
          Object.entries(previous).filter(([name]) => availableNames.has(name)),
        ))
      } catch (err) {
        if (!controller.signal.aborted) {
          setCatalogError(errorMessage(err))
        }
      } finally {
        if (catalogRequestRef.current?.controller === controller) {
          catalogRequestRef.current = null
        }
        setCatalogLoading(false)
      }
    })()
    catalogRequestRef.current = { controller, promise }
    await promise
  }, [])

  const loadView = useCallback(async (viewName = selectedRef.current) => {
    if (!viewName || !reportViewsRef.current.some((view) => view.name === viewName)) return

    while (viewRequestRef.current) {
      const activeRequest = viewRequestRef.current
      if (activeRequest.viewName === viewName && !activeRequest.controller.signal.aborted) {
        await activeRequest.promise
        return
      }

      activeRequest.controller.abort()
      await activeRequest.promise
      if (
        selectedRef.current !== viewName
        || !reportViewsRef.current.some((view) => view.name === viewName)
      ) return
    }

    if (
      selectedRef.current !== viewName
      || !reportViewsRef.current.some((view) => view.name === viewName)
    ) return

    const controller = new AbortController()
    setLoadingView(viewName)
    setViewErrors((previous) => {
      const next = { ...previous }
      delete next[viewName]
      return next
    })

    const promise = (async () => {
      try {
        const { data } = await api.reportes.get<unknown>(`/vistas/${encodeURIComponent(viewName)}`, {
          params: { _refresh: Date.now() },
          signal: controller.signal,
        })
        if (
          controller.signal.aborted
          || selectedRef.current !== viewName
          || viewRequestRef.current?.controller !== controller
          || !Array.isArray(data)
          || !data.every(isRecord)
        ) {
          if (!controller.signal.aborted && selectedRef.current === viewName) {
            throw new Error('El servicio devolvió datos de reporte inválidos.')
          }
          return
        }

        setRowsByView((previous) => ({ ...previous, [viewName]: data as Row[] }))
        setLastUpdatedByView((previous) => ({ ...previous, [viewName]: Date.now() }))
      } catch (err) {
        if (!controller.signal.aborted && selectedRef.current === viewName) {
          setViewErrors((previous) => ({ ...previous, [viewName]: errorMessage(err) }))
        }
      } finally {
        if (viewRequestRef.current?.controller === controller) {
          viewRequestRef.current = null
        }
        setLoadingView((currentView) => currentView === viewName ? null : currentView)
      }
    })()
    viewRequestRef.current = { viewName, controller, promise }
    await promise
  }, [])

  useEffect(() => {
    if (selected) void loadView(selected)
  }, [loadView, selected])

  useEffect(() => {
    void loadCatalog()
    const intervalId = window.setInterval(() => {
      void loadCatalog()
      void loadView(selectedRef.current)
    }, 30_000)

    return () => {
      window.clearInterval(intervalId)
      catalogRequestRef.current?.controller.abort()
      viewRequestRef.current?.controller.abort()
    }
  }, [loadCatalog, loadView])

  const columns = useMemo(
    () => rows.length
      ? Object.keys(rows[0])
      : current?.columns.map((column) => column.name) ?? [],
    [current, rows],
  )
  const filteredViews = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('es-CO')
    if (!query) return reportViews
    return reportViews.filter((view) =>
      `${view.label} ${view.name} ${view.description ?? ''}`.toLocaleLowerCase('es-CO').includes(query),
    )
  }, [reportViews, search])

  const visibleRows = rows.slice(page * limit, (page + 1) * limit)
  const totalPages = Math.max(1, Math.ceil(rows.length / limit))
  const refresh = () => {
    void loadCatalog()
    if (selectedRef.current) void loadView(selectedRef.current)
  }

  return (
    <>
      <PageHeader
        eyebrow="Análisis"
        title="Reportes"
        description="Consulta las vistas autorizadas disponibles en el servicio de Reportes."
        action={
          <button
            type="button"
            className="button button-outline"
            onClick={refresh}
            disabled={catalogLoading && loading}
          >
            <RefreshCw size={16} className={catalogLoading || loading ? 'spin' : ''} />
            Actualizar
          </button>
        }
      />

      <section className="home-section">
        <div className="section-heading">
          <div>
            <h2>Reportes disponibles</h2>
            <p>El catálogo se actualiza automáticamente cada 30 segundos.</p>
          </div>
          <span className="report-count">{reportViews.length} vistas</span>
        </div>

        {catalogError && (
          <div className="notice notice-error">
            <AlertCircle size={17} />
            <span>{catalogError}</span>
            <button type="button" onClick={() => void loadCatalog()}>Reintentar</button>
          </div>
        )}

        {reportViews.length > 0 && (
          <label className="search-field">
            <Search size={15} aria-hidden="true" />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar reportes..."
              aria-label="Buscar reportes"
            />
          </label>
        )}

        {catalogLoading && reportViews.length === 0 ? (
          <div className="table-state">
            <LoaderCircle size={17} className="spin" />
            Cargando catálogo de reportes...
          </div>
        ) : reportViews.length === 0 ? (
          <div className="empty-feature report-empty">
            <h2>No hay vistas disponibles</h2>
            <p>El catálogo no contiene vistas autorizadas para consulta.</p>
          </div>
        ) : filteredViews.length === 0 ? (
          <p className="table-state">No hay vistas que coincidan con la búsqueda.</p>
        ) : (
          <div className="report-selector">
            {filteredViews.map((view) => (
              <button
                type="button"
                key={`${view.schema}.${view.name}`}
                className={`report-option ${selected === view.name ? 'report-option-active' : ''}`}
                aria-pressed={selected === view.name}
                onClick={() => {
                  selectedRef.current = view.name
                  setSelected(view.name)
                  setPage(0)
                }}
              >
                <span className="report-option-title">{view.label}</span>
                <span className="report-option-status">
                  <CheckCircle2 size={13} /> {view.schema}
                </span>
              </button>
            ))}
          </div>
        )}
      </section>

      {current && (
        <section className="home-section">
        <div className="section-heading">
          <div>
            <h2>{current.label}</h2>
            <p>{current.description ?? `Vista ${current.schema}.${current.name}`}</p>
          </div>
          <span className="report-count">
            {rows.length} registros
            {selected && lastUpdatedByView[selected] && (
              <> · Actualizado: {new Date(lastUpdatedByView[selected]).toLocaleString('es-CO')}</>
            )}
          </span>
        </div>

        {error && (
          <div className="notice notice-error">
            <AlertCircle size={17} />
            <span>{error}</span>
            <button type="button" onClick={() => void loadView(selected)}>Reintentar</button>
          </div>
        )}

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
                {loading && rows.length === 0 ? (
                  <tr>
                    <td colSpan={Math.max(columns.length, 1)} className="table-state">
                      <LoaderCircle size={17} className="spin" />
                      Cargando reporte...
                    </td>
                  </tr>
                ) : error && rows.length === 0 ? (
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

          {!loading && rows.length > 0 && (
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
        </section>
      )}
    </>
  )
}
