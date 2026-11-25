import { ArrowDownToLine, Eye, PackagePlus, Plus, RefreshCw, XCircle } from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../../lib/api'
import { displayDate } from '../../lib/format'
import { DataTable, type TableColumn } from '../../components/common/DataTable'
import { FieldInput, type FieldDefinition } from '../../components/common/FieldInput'
import { Modal } from '../../components/common/Modal'
import { Notice } from '../../components/common/Notice'
import { PageHeader } from '../../components/common/PageHeader'
import { StatusBadge } from '../../components/common/StatusBadge'

type Row = Record<string, unknown>
type TransferLine = { id_transferencia: number; id_producto: number; cantidad_enviada: number; cantidad_recibida: number | null }
type Product = { id_producto: number; nombre: string; sku: string; estado: string }

const stockFilters: FieldDefinition[] = [
  { name: 'id_sede', label: 'Sede', type: 'select', remote: { service: 'organizacion', path: '/sedes', value: 'id_sede', label: 'nombre', params: { estado: 'activo' } } },
  { name: 'id_almacen', label: 'Almacén', type: 'select', remote: { service: 'organizacion', path: '/warehouses', value: 'id_almacen', label: 'nombre', params: { estado: 'activo' } } },
  { name: 'id_producto', label: 'Producto', type: 'select', remote: { service: 'catalogo', path: '/products', value: 'id_producto', label: 'nombre', params: { estado: 'activo' } } },
]

export function InventoryPage({ view = 'stock' }: { view?: 'stock' | 'alerts' | 'transfers' }) {
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)
  const [offset, setOffset] = useState(0)
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [applied, setApplied] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)
  const [modal, setModal] = useState<'adjust' | 'createTransfer' | 'transferDetails' | 'receive' | null>(null)
  const [selectedTransfer, setSelectedTransfer] = useState<Row | null>(null)
  const [transferLines, setTransferLines] = useState<TransferLine[]>([])
  const [saving, setSaving] = useState(false)
  const [adjustFields, setAdjustFields] = useState({ id_almacen: '', id_producto: '' })
  const limit = 20
  const reportError = useCallback((text: string) => setNotice({ kind: 'error', text }), [])

  const load = useCallback(async () => {
    setLoading(true)
    setNotice(null)
    try {
      const path = view === 'transfers' ? '/transfers' : view === 'alerts' ? '/stock/alerts' : '/stock'
      const params: Record<string, string | number> = { limit, offset }
      if (view === 'alerts') {
        if (applied.id_sede) params.id_sede = applied.id_sede
        if (applied.id_almacen) params.id_almacen = applied.id_almacen
      } else if (view === 'stock') {
        Object.entries(applied).forEach(([key, value]) => { if (value) params[key] = value })
      }
      const { data } = await api.inventarios.get<Row[]>(path, { params })
      setRows(Array.isArray(data) ? data : [])
    } catch (error) {
      setRows([])
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setLoading(false)
    }
  }, [applied, offset, view])

  useEffect(() => { void load() }, [load])

  async function showTransfer(row: Row) {
    setSelectedTransfer(row)
    setModal('transferDetails')
    try {
      const { data } = await api.inventarios.get<TransferLine[]>(`/transfers/${row.id_transferencia}/details`)
      setTransferLines(data)
    } catch (error) {
      setTransferLines([])
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  async function startTransferReceipt(row: Row) {
    setSelectedTransfer(row)
    try {
      const { data } = await api.inventarios.get<TransferLine[]>(`/transfers/${row.id_transferencia}/details`)
      setTransferLines(data)
      setModal('receive')
    } catch (error) {
      setTransferLines([])
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  async function performTransferAction(action: 'dispatch' | 'cancel', row: Row) {
    const label = action === 'dispatch' ? 'despachar' : 'cancelar'
    if (!window.confirm(`¿${label[0].toUpperCase()}${label.slice(1)} la transferencia ${row.id_transferencia}?`)) return
    try {
      await api.inventarios.post(`/transfers/${row.id_transferencia}/${action}`)
      setNotice({ kind: 'success', text: `Transferencia ${action === 'dispatch' ? 'despachada' : 'cancelada'}.` })
      await load()
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  async function submitAdjustment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const target = Number(formData.get('existencia_objetivo'))
    if (!adjustFields.id_almacen || !adjustFields.id_producto || !Number.isInteger(target) || target < 0) {
      setNotice({ kind: 'error', text: 'Selecciona un almacén y un producto, e ingresa una existencia entera no negativa.' })
      return
    }
    setSaving(true)
    try {
      await api.inventarios.post('/stock/adjustments', {
        id_almacen: Number(adjustFields.id_almacen),
        id_producto: Number(adjustFields.id_producto),
        existencia_objetivo: target,
      })
      setModal(null)
      setNotice({ kind: 'success', text: 'Existencia actualizada.' })
      await load()
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setSaving(false)
    }
  }

  async function submitReceive(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedTransfer) return
    const formData = new FormData(event.currentTarget)
    setSaving(true)
    try {
      await api.inventarios.put(`/transfers/${selectedTransfer.id_transferencia}/receipts`, {
        productos: transferLines.map((line) => ({
          id_producto: line.id_producto,
          cantidad_total_recibida: Number(formData.get(`received-${line.id_producto}`) ?? line.cantidad_recibida ?? 0),
        })),
      })
      setModal(null)
      setNotice({ kind: 'success', text: 'Recepción registrada. El inventario se incrementó únicamente por las unidades nuevas recibidas.' })
      await load()
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setSaving(false)
    }
  }

  const isTransfer = view === 'transfers'
  const columns: TableColumn<Row>[] = isTransfer
    ? [
      { key: 'id_transferencia', label: 'Transferencia' },
      { key: 'id_almacen_origen', label: 'Origen' },
      { key: 'id_almacen_destino', label: 'Destino' },
      { key: 'fecha_solicitud', label: 'Solicitud', render: (row) => displayDate(row.fecha_solicitud) },
      { key: 'fecha_despacho', label: 'Despacho', render: (row) => displayDate(row.fecha_despacho) },
      { key: 'estado', label: 'Estado', render: (row) => <StatusBadge value={row.estado} /> },
      {
        key: 'acciones',
        label: 'Acciones',
        render: (row) => (
          <div className="row-actions">
            <button type="button" className="icon-button" title="Ver detalle" aria-label="Ver detalle" onClick={() => void showTransfer(row)}><Eye size={16} /></button>
            {row.estado === 'solicitada' && (
              <>
                <button type="button" className="icon-button icon-success" title="Despachar" aria-label="Despachar" onClick={() => void performTransferAction('dispatch', row)}><ArrowDownToLine size={16} /></button>
                <button type="button" className="icon-button icon-danger" title="Cancelar" aria-label="Cancelar" onClick={() => void performTransferAction('cancel', row)}><XCircle size={16} /></button>
              </>
            )}
            {row.estado === 'despachada' && (
              <button type="button" className="icon-button icon-success" title="Recibir" aria-label="Recibir" onClick={() => void startTransferReceipt(row)}><PackagePlus size={16} /></button>
            )}
          </div>
        ),
      },
    ]
    : [
      { key: 'id_sede', label: 'Sede' },
      { key: 'id_almacen', label: 'Almacén' },
      { key: 'id_producto', label: 'Producto' },
      { key: 'existencia_actual', label: 'Existencia' },
      { key: 'stock_minimo', label: 'Mínimo' },
      { key: 'fecha_actualizacion', label: 'Actualizado', render: (row) => displayDate(row.fecha_actualizacion) },
    ]

  const title = view === 'transfers' ? 'Transferencias' : view === 'alerts' ? 'Alertas de stock' : 'Existencias'
  return (
    <>
      <PageHeader
        eyebrow="Inventarios"
        title={title}
        description={view === 'transfers' ? 'Movimientos entre almacenes con despacho y recepción controlados.' : 'Existencias registradas por sede, almacén y producto.'}
        action={view === 'transfers'
          ? <button className="button button-primary" onClick={() => setModal('createTransfer')}><Plus size={17} /> Nueva transferencia</button>
          : view === 'stock'
            ? <button className="button button-primary" onClick={() => setModal('adjust')}><PackagePlus size={17} /> Ajustar existencia</button>
            : undefined}
      />
      {notice && <Notice kind={notice.kind} onDismiss={() => setNotice(null)}>{notice.text}</Notice>}
      <div className="filter-bar">
        <div className="tabs" aria-label="Inventarios">
          <Link className={`tab-link ${view === 'stock' ? 'tab-active' : ''}`} to="/inventory/stock">Existencias</Link>
          <Link className={`tab-link ${view === 'alerts' ? 'tab-active' : ''}`} to="/inventory/alerts">Alertas</Link>
          <Link className={`tab-link ${view === 'transfers' ? 'tab-active' : ''}`} to="/inventory/transfers">Transferencias</Link>
        </div>
        <button type="button" className="button button-quiet" onClick={() => void load()} disabled={loading}><RefreshCw size={16} className={loading ? 'spin' : ''} /> Actualizar</button>
      </div>
      {view !== 'transfers' && (
        <form className="filter-bar filter-form" onSubmit={(event) => {
          event.preventDefault()
          setOffset(0)
          setApplied({ ...filters })
        }}>
          {stockFilters.slice(0, view === 'alerts' ? 2 : 3).map((field) => (
            <FieldInput
              key={field.name}
              field={field}
              value={filters[field.name] ?? ''}
              onChange={(value) => setFilters((current) => ({ ...current, [field.name]: value }))}
            />
          ))}
          <button type="submit" className="button button-outline">Aplicar filtros</button>
        </form>
      )}
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
      {modal === 'adjust' && (
        <Modal title="Ajustar existencia" description="Se establece la cantidad actual. No se registra un historial de ajustes en el esquema." onClose={() => !saving && setModal(null)}>
          <form className="form-grid" onSubmit={(event) => void submitAdjustment(event)}>
            <FieldInput field={{ name: 'id_almacen', label: 'Almacén', type: 'select', required: true, remote: { service: 'organizacion', path: '/warehouses', value: 'id_almacen', label: 'nombre', params: { estado: 'activo' } } }} value={adjustFields.id_almacen} onChange={(value) => setAdjustFields((current) => ({ ...current, id_almacen: value }))} />
            <FieldInput field={{ name: 'id_producto', label: 'Producto', type: 'select', required: true, remote: { service: 'catalogo', path: '/products', value: 'id_producto', label: 'nombre', params: { estado: 'activo' } } }} value={adjustFields.id_producto} onChange={(value) => setAdjustFields((current) => ({ ...current, id_producto: value }))} />
            <label className="form-field"><span>Existencia objetivo</span><input type="number" name="existencia_objetivo" min={0} required /></label>
            <div className="form-actions"><button type="button" className="button button-outline" onClick={() => setModal(null)}>Cancelar</button><button className="button button-primary" disabled={saving}>{saving ? 'Guardando…' : 'Guardar ajuste'}</button></div>
          </form>
        </Modal>
      )}
      {modal === 'createTransfer' && (
        <CreateTransferModal
          onClose={() => setModal(null)}
          onError={reportError}
          onCreated={async () => {
            setModal(null)
            setNotice({ kind: 'success', text: 'Transferencia creada en estado solicitada.' })
            await load()
          }}
        />
      )}
      {modal === 'transferDetails' && selectedTransfer && (
        <Modal title={`Transferencia #${selectedTransfer.id_transferencia}`} description="Unidades enviadas y acumulado recibido." onClose={() => setModal(null)}>
          <DataTable
            columns={[
              { key: 'id_producto', label: 'Producto' },
              { key: 'cantidad_enviada', label: 'Enviado' },
              { key: 'cantidad_recibida', label: 'Recibido', render: (row) => String(row.cantidad_recibida ?? 0) },
            ]}
            rows={transferLines as unknown as Row[]}
          />
          {selectedTransfer.estado === 'despachada' && <div className="form-actions"><button type="button" className="button button-primary" onClick={() => setModal('receive')}><PackagePlus size={16} /> Registrar recepción</button></div>}
        </Modal>
      )}
      {modal === 'receive' && selectedTransfer && (
        <Modal title={`Recepción de transferencia #${selectedTransfer.id_transferencia}`} description="Indica las cantidades totales recibidas por producto. Solo se sumará la diferencia respecto a lo registrado." onClose={() => !saving && setModal(null)}>
          <form className="receive-list" onSubmit={(event) => void submitReceive(event)}>
            {transferLines.map((line) => (
              <label className="receive-line" key={line.id_producto}>
                <span>Producto {line.id_producto}<small>Enviado {line.cantidad_enviada} · recibido {line.cantidad_recibida ?? 0}</small></span>
                <input type="number" name={`received-${line.id_producto}`} min={line.cantidad_recibida ?? 0} max={line.cantidad_enviada} defaultValue={line.cantidad_recibida ?? 0} required />
              </label>
            ))}
            <div className="form-actions"><button type="button" className="button button-outline" onClick={() => setModal(null)} disabled={saving}>Cancelar</button><button className="button button-primary" disabled={saving}>{saving ? 'Registrando…' : 'Registrar recepción'}</button></div>
          </form>
        </Modal>
      )}
    </>
  )
}

function CreateTransferModal({
  onClose,
  onCreated,
  onError,
}: {
  onClose: () => void
  onCreated: () => Promise<void>
  onError: (message: string) => void
}) {
  const [source, setSource] = useState('')
  const [destination, setDestination] = useState('')
  const [products, setProducts] = useState<Product[]>([])
  const [cart, setCart] = useState<Array<{ id_producto: number; nombre: string; cantidad_enviada: number }>>([])
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    api.catalogo.get<Product[]>('/products', { params: { estado: 'activo', limit: 100 } })
      .then(({ data }) => { if (active) setProducts(data) })
      .catch((error) => { if (active) onError(errorMessage(error)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [onError])

  function addProduct() {
    const product = products.find((item) => item.id_producto === Number(productId))
    const count = Number(quantity)
    if (!product || !Number.isInteger(count) || count < 1 || cart.some((item) => item.id_producto === product.id_producto)) return
    setCart((current) => [...current, { id_producto: product.id_producto, nombre: product.nombre, cantidad_enviada: count }])
    setProductId('')
    setQuantity('1')
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!cart.length) {
      onError('Agrega por lo menos un producto a la transferencia.')
      return
    }
    if (source === destination) {
      onError('El almacén de origen debe ser diferente al de destino.')
      return
    }
    setSaving(true)
    try {
      await api.inventarios.post('/transfers', {
        id_almacen_origen: Number(source),
        id_almacen_destino: Number(destination),
        productos: cart.map(({ id_producto, cantidad_enviada }) => ({ id_producto, cantidad_enviada })),
      })
      await onCreated()
    } catch (error) {
      onError(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title="Nueva transferencia" description="La existencia de origen se descuenta únicamente al despachar." onClose={() => !saving && onClose()}>
      <form className="form-grid" onSubmit={(event) => void submit(event)}>
        <FieldInput field={{ name: 'origen', label: 'Almacén de origen', type: 'select', required: true, remote: { service: 'organizacion', path: '/warehouses', value: 'id_almacen', label: 'nombre', params: { estado: 'activo' } } }} value={source} onChange={setSource} />
        <FieldInput field={{ name: 'destino', label: 'Almacén de destino', type: 'select', required: true, remote: { service: 'organizacion', path: '/warehouses', value: 'id_almacen', label: 'nombre', params: { estado: 'activo' } } }} value={destination} onChange={setDestination} />
        <div className="form-field form-field-wide">
          <span>Productos {!products.length && loading ? '· cargando catálogo…' : ''}</span>
          <div className="inline-product-add">
            <select value={productId} onChange={(event) => setProductId(event.target.value)}><option value="">Selecciona un producto</option>{products.map((product) => <option key={product.id_producto} value={product.id_producto}>{product.sku} · {product.nombre}</option>)}</select>
            <input type="number" aria-label="Cantidad enviada" min={1} value={quantity} onChange={(event) => setQuantity(event.target.value)} />
            <button type="button" className="button button-outline" onClick={addProduct}>Agregar</button>
          </div>
          {cart.map((item) => <div className="cart-line" key={item.id_producto}><span>{item.nombre}<small>Enviar: {item.cantidad_enviada}</small></span><button type="button" className="icon-button icon-danger" aria-label={`Quitar ${item.nombre}`} onClick={() => setCart((current) => current.filter((entry) => entry.id_producto !== item.id_producto))}>×</button></div>)}
        </div>
        <div className="form-actions"><button type="button" className="button button-outline" onClick={onClose}>Cancelar</button><button className="button button-primary" disabled={saving}>{saving ? 'Creando…' : 'Crear transferencia'}</button></div>
      </form>
    </Modal>
  )
}
