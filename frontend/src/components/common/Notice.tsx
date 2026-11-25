import { CircleAlert, CircleCheck, Info } from 'lucide-react'

export function Notice({
  kind = 'error',
  children,
  onDismiss,
}: {
  kind?: 'error' | 'success' | 'info'
  children: string
  onDismiss?: () => void
}) {
  const Icon = kind === 'success' ? CircleCheck : kind === 'info' ? Info : CircleAlert
  return (
    <div className={`notice notice-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <Icon size={18} />
      <span>{children}</span>
      {onDismiss && <button type="button" aria-label="Cerrar mensaje" onClick={onDismiss}>×</button>}
    </div>
  )
}
