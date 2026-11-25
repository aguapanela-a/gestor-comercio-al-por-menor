import { ChevronLeft, ChevronRight, LoaderCircle } from 'lucide-react'
import type { ReactNode } from 'react'

export interface TableColumn<T> {
  key: keyof T | string
  label: string
  render?: (row: T) => ReactNode
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
  loading,
  emptyMessage = 'No hay registros para mostrar.',
  offset,
  limit,
  onPrevious,
  onNext,
  canNext,
}: {
  columns: TableColumn<T>[]
  rows: T[]
  loading?: boolean
  emptyMessage?: string
  offset?: number
  limit?: number
  onPrevious?: () => void
  onNext?: () => void
  canNext?: boolean
}) {
  return (
    <div className="table-card">
      <div className="table-scroll">
        <table>
          <thead>
            <tr>{columns.map((column) => <th key={String(column.key)}>{column.label}</th>)}</tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className="table-state" colSpan={columns.length}>
                <LoaderCircle className="spin" size={18} /> Consultando información…
              </td></tr>
            ) : rows.length === 0 ? (
              <tr><td className="table-state" colSpan={columns.length}>{emptyMessage}</td></tr>
            ) : rows.map((row, index) => (
              <tr key={String(row.id ?? row.id_producto ?? row.id_pedido ?? row.id_orden_compra ?? row.id_transferencia ?? index)}>
                {columns.map((column) => (
                  <td key={String(column.key)}>
                    {column.render
                      ? column.render(row)
                      : String(row[String(column.key)] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {offset !== undefined && limit !== undefined && onPrevious && onNext && (
        <div className="table-footer">
          <span>{rows.length ? `${offset + 1}–${offset + rows.length} registros` : 'Sin registros'}</span>
          <div className="pagination">
            <button type="button" className="button button-outline button-small" disabled={offset === 0 || loading} onClick={onPrevious}>
              <ChevronLeft size={16} /> Anterior
            </button>
            <button type="button" className="button button-outline button-small" disabled={!canNext || loading} onClick={onNext}>
              Siguiente <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
