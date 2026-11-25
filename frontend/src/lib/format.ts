export const money = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 2,
})

export function displayDate(value: unknown): string {
  if (!value) return '—'
  const parsed = new Date(String(value))
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleDateString('es-CO')
}

export function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Sí' : 'No'
  return String(value)
}

export function titleCase(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\p{L}/gu, (letter) => letter.toLocaleUpperCase('es-CO'))
}
