import { titleCase } from '../../lib/format'

export function StatusBadge({ value }: { value: unknown }) {
  const state = String(value ?? 'sin estado')
  const tone = ['activo', 'completado', 'aprobada', 'procesada'].includes(state)
    ? 'success'
    : ['pendiente', 'solicitada', 'recibida_parcial', 'despachada'].includes(state)
      ? 'warning'
      : ['inactivo', 'cancelado', 'cancelada', 'rechazada', 'anulada'].includes(state)
        ? 'muted'
        : 'neutral'
  return <span className={`status-badge status-${tone}`}>{titleCase(state)}</span>
}
