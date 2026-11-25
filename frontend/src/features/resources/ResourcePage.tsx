import { Pencil, Plus, RefreshCw, Search, ShieldCheck, UserRoundX } from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, errorMessage } from '../../lib/api'
import { displayDate, displayValue, money } from '../../lib/format'
import { DataTable, type TableColumn } from '../../components/common/DataTable'
import { FieldInput, type FieldDefinition } from '../../components/common/FieldInput'
import { Modal } from '../../components/common/Modal'
import { Notice } from '../../components/common/Notice'
import { PageHeader } from '../../components/common/PageHeader'
import { StatusBadge } from '../../components/common/StatusBadge'
import { resourceDefinitions, type ResourceDefinition } from './config'

type DataRow = Record<string, unknown>

function formatCell(key: string, value: unknown) {
  if (key === 'estado') return <StatusBadge value={value} />
  if (key.startsWith('fecha')) return displayDate(value)
  if (key === 'precio_lista' || key === 'costo_referencia') {
    const number = Number(value)
    return Number.isNaN(number) ? displayValue(value) : money.format(number)
  }
  return displayValue(value)
}

function fieldsForForm(fields: FieldDefinition[], editing: boolean) {
  return fields.filter((field) => !(editing && field.createOnly) && !(!editing && field.editOnly))
}

export function ResourcePage({ resourceKey }: { resourceKey: string }) {
  const definition = resourceDefinitions[resourceKey]
  if (!definition) return <p>El recurso solicitado no está configurado.</p>
  return <ResourceView key={resourceKey} definition={definition} resourceKey={resourceKey} />
}

function ResourceView({
  definition,
  resourceKey,
}: {
  definition: ResourceDefinition
  resourceKey: string
}) {
  const [rows, setRows] = useState<DataRow[]>([])
  const [loading, setLoading] = useState(false)
  const [offset, setOffset] = useState(0)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [appliedSearch, setAppliedSearch] = useState('')
  const [appliedFilters, setAppliedFilters] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState<{ kind: 'error' | 'success' | 'info'; text: string } | null>(null)
  const [editing, setEditing] = useState<DataRow | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [formValues, setFormValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const limit = definition.limit ?? 20

  const load = useCallback(async () => {
    setLoading(true)
    setNotice(null)
    try {
      const params: Record<string, string | number> = { limit, offset }
      if (appliedSearch && definition.searchParam) params[definition.searchParam] = appliedSearch
      Object.entries(appliedFilters).forEach(([key, value]) => {
        if (value) params[key] = value
      })
      const { data } = await api[definition.service].get<DataRow[]>(definition.path, { params })
      setRows(Array.isArray(data) ? data : [])
    } catch (error) {
      setRows([])
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setLoading(false)
    }
  }, [appliedFilters, appliedSearch, definition, limit, offset])

  useEffect(() => { void load() }, [load])

  const columns: TableColumn<DataRow>[] = definition.columns.map((column) => ({
    ...column,
    render: (row: DataRow) => formatCell(String(column.key), row[String(column.key)]),
  }))
  if (definition.actions !== false && (definition.update || definition.deactivate)) {
    columns.push({
      key: '__actions',
      label: 'Acciones',
      render: (row) => (
        <div className="row-actions">
          {definition.update && (
            <button type="button" className="icon-button" aria-label={`Editar ${definition.singular}`} title="Editar" onClick={() => openEdit(row)}>
              <Pencil size={16} />
            </button>
          )}
          {definition.deactivate && row.estado === 'activo' && (
            <button type="button" className="icon-button icon-danger" aria-label={`Inactivar ${definition.singular}`} title="Inactivar" onClick={() => void deactivate(row)}>
              <UserRoundX size={16} />
            </button>
          )}
        </div>
      ),
    })
  }

  function openCreate() {
    setEditing(null)
    setFormValues(Object.fromEntries(
      definition.fields.map((field) => [field.name, field.name === 'estado' ? 'activo' : '']),
    ))
    setShowForm(true)
  }

  function openEdit(row: DataRow) {
    setEditing(row)
    setFormValues(Object.fromEntries(
      fieldsForForm(definition.fields, true).map((field) => [
        field.name,
        displayFormValue(row[field.name]),
      ]),
    ))
    setShowForm(true)
  }

  function applySearch(event: FormEvent) {
    event.preventDefault()
    setOffset(0)
    setAppliedSearch(search.trim())
    setAppliedFilters({ ...filters })
  }

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload: Record<string, unknown> = {}
    fieldsForForm(definition.fields, Boolean(editing)).forEach((field) => {
      const value = formValues[field.name] ?? ''
      if (value === '') return
      payload[field.name] = field.type === 'number' || field.name.startsWith('id_')
        ? Number(value)
        : value
    })
    setSaving(true)
    try {
      const client = api[definition.service]
      if (editing) {
        const id = editing[definition.idField]
        if (id === undefined) throw new Error('No se pudo determinar el identificador del recurso.')
        const path = definition.updatePath?.(editing) ?? definition.rowPath?.(editing) ?? `${definition.path}/${id}`
        if (definition.updateMethod === 'put') await client.put(path, payload)
        else await client.patch(path, payload)
      } else {
        const path = definition.createPathFromPayload?.(payload) ?? definition.createPath ?? definition.path
        if (definition.createMethod === 'put') await client.put(path, payload)
        else await client.post(path, payload)
      }
      setShowForm(false)
      setEditing(null)
      setNotice({ kind: 'success', text: `${definition.singular[0].toLocaleUpperCase('es-CO')}${definition.singular.slice(1)} ${editing ? 'actualizado' : 'creado'} correctamente.` })
      await load()
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setSaving(false)
    }
  }

  async function deactivate(row: DataRow) {
    if (!window.confirm(`¿Inactivar este ${definition.singular}?`)) return
    try {
      const path = definition.deactivatePath?.(row) ?? `${definition.path}/${row[definition.idField]}`
      await api[definition.service].delete(path)
      setNotice({ kind: 'success', text: `${definition.singular} inactivado correctamente.` })
      await load()
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  return (
    <>
      <PageHeader
        eyebrow={resourceKey.startsWith('identity') ? 'Identidad' : undefined}
        title={definition.title}
        description={definition.description}
        action={definition.create ? (
          <button type="button" className="button button-primary" onClick={openCreate}>
            <Plus size={17} /> Nuevo {definition.singular}
          </button>
        ) : undefined}
      />
      {notice && <Notice kind={notice.kind} onDismiss={() => setNotice(null)}>{notice.text}</Notice>}
      {resourceKey === 'users' && (
        <div className="info-strip">
          <ShieldCheck size={18} />
          <span>Las contraseñas no se muestran. Puedes cambiar la de tu sesión desde Seguridad.</span>
          <button type="button" className="text-button" onClick={() => setPasswordOpen(true)}>Cambiar mi contraseña</button>
        </div>
      )}
      <section className="filter-bar" aria-label={`Filtros de ${definition.title}`}>
        <form className="filter-form" onSubmit={applySearch}>
          {definition.searchParam && (
            <label className="search-field">
              <Search size={17} />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={definition.searchLabel ?? 'Buscar'} />
            </label>
          )}
          {definition.filters?.map((field) => (
            <FieldInput
              key={field.name}
              field={{ ...field, required: false }}
              value={filters[field.name] ?? ''}
              onChange={(value) => setFilters((current) => ({ ...current, [field.name]: value }))}
            />
          ))}
          {(definition.searchParam || definition.filters?.length) && (
            <button type="submit" className="button button-outline">
              <Search size={16} /> Aplicar
            </button>
          )}
        </form>
        <button type="button" className="button button-quiet" onClick={() => void load()} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} /> Actualizar
        </button>
      </section>
      <DataTable
        columns={columns}
        rows={rows}
        loading={loading}
        offset={offset}
        limit={limit}
        canNext={rows.length === limit}
        onPrevious={() => setOffset((current) => Math.max(0, current - limit))}
        onNext={() => setOffset((current) => current + limit)}
      />
      {showForm && (
        <Modal
          title={`${editing ? 'Editar' : 'Crear'} ${definition.singular}`}
          description="Los campos se validan de acuerdo con la API correspondiente."
          onClose={() => { if (!saving) setShowForm(false) }}
        >
          <form className="form-grid" onSubmit={submitForm}>
            {fieldsForForm(definition.fields, Boolean(editing)).map((field) => (
              <FieldInput
                key={field.name}
                field={{ ...field, required: editing ? false : field.required }}
                value={formValues[field.name] ?? ''}
                onChange={(value) => setFormValues((current) => ({ ...current, [field.name]: value }))}
              />
            ))}
            <div className="form-actions">
              <button type="button" className="button button-outline" disabled={saving} onClick={() => setShowForm(false)}>Cancelar</button>
              <button type="submit" className="button button-primary" disabled={saving}>
                {saving ? 'Guardando…' : editing ? 'Guardar cambios' : 'Crear'}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {passwordOpen && <ChangePasswordModal onClose={() => setPasswordOpen(false)} onSuccess={(text) => {
        setPasswordOpen(false)
        setNotice({ kind: 'success', text })
      }} />}
    </>
  )
}

function displayFormValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  return String(value)
}

function ChangePasswordModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void
  onSuccess: (text: string) => void
}) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    const currentPassword = String(values.get('current_password') ?? '')
    const newPassword = String(values.get('new_password') ?? '')
    if (newPassword.length < 1 || newPassword.length > 128) {
      setError('La nueva contraseña debe tener entre 1 y 128 caracteres.')
      return
    }
    setSaving(true)
    try {
      await api.identidad.post('/auth/password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      onSuccess('Contraseña actualizada.')
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title="Cambiar mi contraseña" onClose={onClose}>
      <form className="form-grid" onSubmit={submit}>
        {error && <Notice>{error}</Notice>}
        <label className="form-field form-field-wide">
          <span>Contraseña actual <b className="required-mark">*</b></span>
          <input type="password" name="current_password" required maxLength={128} autoComplete="current-password" />
        </label>
        <label className="form-field form-field-wide">
          <span>Nueva contraseña <b className="required-mark">*</b></span>
          <input type="password" name="new_password" required maxLength={128} autoComplete="new-password" />
        </label>
        <div className="form-actions">
          <button type="button" className="button button-outline" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="button button-primary" disabled={saving}>{saving ? 'Guardando…' : 'Actualizar contraseña'}</button>
        </div>
      </form>
    </Modal>
  )
}
