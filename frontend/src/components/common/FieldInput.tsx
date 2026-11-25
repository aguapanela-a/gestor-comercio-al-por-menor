import { useEffect, useState } from 'react'
import type { ServiceName } from '../../lib/api'
import { api } from '../../lib/api'

export interface SelectOption {
  value: string | number
  label: string
}

export interface FieldDefinition {
  name: string
  label: string
  type?: 'text' | 'number' | 'email' | 'password' | 'date' | 'textarea' | 'select'
  required?: boolean
  min?: number
  max?: number
  maxLength?: number
  placeholder?: string
  createOnly?: boolean
  editOnly?: boolean
  options?: SelectOption[]
  remote?: {
    service: ServiceName
    path: string
    value: string
    label: string
    params?: Record<string, string | number>
  }
}

export function FieldInput({
  field,
  value,
  onChange,
}: {
  field: FieldDefinition
  value: string
  onChange: (value: string) => void
}) {
  const [options, setOptions] = useState<SelectOption[]>(field.options ?? [])
  const [optionError, setOptionError] = useState('')

  useEffect(() => {
    let active = true
    if (!field.remote) return
    api[field.remote.service].get<unknown[]>(field.remote.path, {
      params: { limit: 100, ...field.remote.params },
    })
      .then(({ data }) => {
        if (!active) return
        if (Array.isArray(data)) {
          setOptions(data.map((item) => {
            const row = item as Record<string, unknown>
            return {
              value: String(row[field.remote!.value]),
              label: String(row[field.remote!.label]),
            }
          }))
        }
      })
      .catch(() => {
        if (active) setOptionError('No se pudieron cargar las opciones del servicio.')
      })
    return () => { active = false }
  }, [field.remote])

  const inputId = `field-${field.name}`
  return (
    <label className={`form-field ${field.type === 'textarea' ? 'form-field-wide' : ''}`} htmlFor={inputId}>
      <span>{field.label}{field.required && <b className="required-mark"> *</b>}</span>
      {field.type === 'textarea' ? (
        <textarea
          id={inputId}
          name={field.name}
          value={value}
          required={field.required}
          maxLength={field.maxLength}
          placeholder={field.placeholder}
          onChange={(event) => onChange(event.target.value)}
          rows={3}
        />
      ) : field.type === 'select' ? (
        <>
          <select
            id={inputId}
            name={field.name}
            value={value}
            required={field.required}
            onChange={(event) => onChange(event.target.value)}
          >
            <option value="">Selecciona una opción</option>
            {options.map((option) => (
              <option key={String(option.value)} value={option.value}>{option.label}</option>
            ))}
          </select>
          {optionError && <small className="field-note">{optionError}</small>}
        </>
      ) : (
        <input
          id={inputId}
          name={field.name}
          type={field.type ?? 'text'}
          value={value}
          required={field.required}
          min={field.min}
          max={field.max}
          maxLength={field.maxLength}
          placeholder={field.placeholder}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </label>
  )
}
