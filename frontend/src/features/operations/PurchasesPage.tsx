import { Eye, PackageCheck, Plus, RefreshCw, XCircle } from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../../lib/api'
import { displayDate, money } from '../../lib/format'
import { DataTable, type TableColumn } from '../../components/common/DataTable'
import { FieldInput, type FieldDefinition } from '../../components/common/FieldInput'
import { Modal } from '../../components/common/Modal'
import { Notice } from '../../components/common/Notice'
import { PageHeader } from '../../components/common/PageHeader'
import { StatusBadge } from '../../components/common/StatusBadge'

type Row = Record<string, unknown>
type Product = { id_producto: number; nombre: string; sku: string; estado: string; precio_lista?: number }
type OrderLine = {
  id_orden_compra: number
  id_producto: number
  cantidad_solicitada: number
  costo_unitario: number
  cantidad_recibida: number
  cantidad_pendiente: number
}

const orderFields: FieldDefinition[] = [
  { name: 'id_proveedor', label: 'Proveedor', type: 'select', required: true, remote: { service: 'compras', path: '/suppliers', value: 'id_proveedor', label: 'razon_social', params: { estado: 'activo' } } },
  { name: 'id_almacen_destino', label: 'Almacén de destino', type: 'select', required: true, remote: { service: 'organizacion', path: '/warehouses', value: 'id_almacen', label: 'nombre', params: { estado: 'activo' } } },
  { name: 'id_empleado_creador', label: 'Empleado responsable', type: 'select', required: true, remote: { service: 'identidad', path: '/employees', value: 'id_empleado', label: 'nombre_completo', params: { estado: 'activo' } } },
  { name: 'fecha_estimada', label: 'Fecha estimada', type: 'date', required: true },
]

export function PurchasesPage({ view = 'orders' }: { view?: 'orders' | 'receipts' }) {
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)
  const [offset, setOffset] = useState(0)
  const [notice, setNotice] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)
  const [modal, setModal] = useState<'create' | 'details' | 'receive' | 'receiptDetails' | null>(null)
  const [selectedOrder, setSelectedOrder] = useState<Row | null>(null)
  const [selectedReceipt, setSelectedReceipt] = useState<Row | null>(null)
  const [lines, setLines] = useState<OrderLine[]>([])
  const [receiptLines, setReceiptLines] = useState<Row[]>([])
  const [saving, setSaving] = useState(false)
  const reportError = useCallback((text: string) => setNotice({ kind: 'error', text }), [])
  const limit = 20

  const load = useCallback(async () => {
    setLoading(true)
    setNotice(null)
    try {
      const path = view === 'orders' ? '/purchase-orders' : '/receipts'
      const { data } = await api.compras.get<Row[]>(path, { params: { limit, offset } })
      setRows(Array.isArray(data) ? data : [])
    } catch (error) {
      setRows([])
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setLoading(false)
    }
  }, [offset, view])

  useEffect(() => { void load() }, [load])

  async function showOrder(order: Row) {
    setSelectedOrder(order)
    setModal('details')
    try {
      const { data } = await api.compras.get<OrderLine[]>(`/purchase-orders/${order.id_orden_compra}/details`)
      setLines(data)
    } catch (error) {
      setLines([])
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  async function showReceipt(receipt: Row) {
    setSelectedReceipt(receipt)
    setModal('receiptDetails')
    try {
      const { data } = await api.compras.get<Row[]>(`/receipts/${receipt.id_recepcion}/details`)
      setReceiptLines(data)
    } catch (error) {
      setReceiptLines([])
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  function startReceipt() {
    setModal('receive')
  }

  async function cancelOrder(order: Row) {
    if (!window.confirm(`¿Cancelar la orden ${order.id_orden_compra}? Solo se pueden cancelar órdenes pendientes.`)) return
    try {
      await api.compras.post(`/purchase-orders/${order.id_orden_compra}/cancel`)
      setNotice({ kind: 'success', text: 'Orden cancelada.' })
      await load()
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  async function submitReceipt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedOrder) return
    const formData = new FormData(event.currentTarget)
    const products = lines.map((line) => ({
      id_producto: line.id_producto,
      cantidad_total_recibida: Number(formData.get(`received-${line.id_producto}`) ?? line.cantidad_recibida),
    }))
    setSaving(true)
    try {
      const { data } = await api.compras.post(
        `/receipts/purchase-orders/${selectedOrder.id_orden_compra}`,
        { productos: products },
      )
      setModal(null)
      setNotice({
        kind: 'success',
        text: data.cantidades_actualizadas ? 'Recepción registrada y estado de la orden actualizado.' : 'Las cantidades ya estaban registradas; no se duplicó la recepción.',
      })
      await load()
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setSaving(false)
    }
  }

  const columns: TableColumn<Row>[] = view === 'orders'
    ? [
      { key: 'id_orden_compra', label: 'Orden' },
      { key: 'id_proveedor', label: 'Proveedor' },
      { key: 'id_almacen_destino', label: 'Almacén' },
      { key: 'fecha_orden', label: 'Fecha', render: (row) => displayDate(row.fecha_orden) },
      { key: 'fecha_estimada', label: 'Entrega estimada', render: (row) => displayDate(row.fecha_estimada) },
      { key: 'estado', label: 'Estado', render: (row) => <StatusBadge value={row.estado} /> },
      {
        key: 'acciones',
        label: 'Acciones',
        render: (row) => (
          <div className="row-actions">
            <button type="button" className="icon-button" title="Ver detalle" aria-label="Ver detalle" onClick={() => void showOrder(row)}><Eye size={16} /></button>
            {['pendiente', 'recibida_parcial'].includes(String(row.estado)) && (
              <button type="button" className="icon-button icon-success" title="Registrar recepción" aria-label="Registrar recepción" onClick={() => { setSelectedOrder(row); void showOrder(row).then(startReceipt) }}><PackageCheck size={16} /></button>
            )}
            {row.estado === 'pendiente' && (
              <button type="button" className="icon-button icon-danger" title="Cancelar orden" aria-label="Cancelar orden" onClick={() => void cancelOrder(row)}><XCircle size={16} /></button>
            )}
          </div>
        ),
      },
    ]
    : [
      { key: 'id_recepcion', label: 'Recepción' },
      { key: 'id_orden_compra', label: 'Orden' },
      { key: 'fecha_recepcion', label: 'Fecha', render: (row) => displayDate(row.fecha_recepcion) },
      { key: 'estado', label: 'Estado', render: (row) => <StatusBadge value={row.estado} /> },
      { key: 'acciones', label: 'Detalle', render: (row) => <button type="button" className="icon-button" aria-label="Ver detalle" title="Ver detalle" onClick={() => void showReceipt(row)}><Eye size={16} /></button> },
    ]

  return (
    <>
      <PageHeader
        eyebrow="Compras"
        title={view === 'orders' ? 'Órdenes de compra' : 'Recepciones'}
        description={view === 'orders' ? 'Órdenes y cumplimiento de cantidades por producto.' : 'Historial de recepciones registradas y sus líneas.'}
        action={view === 'orders' ? <button className="button button-primary" onClick={() => setModal('create')}><Plus size={17} /> Nueva orden</button> : undefined}
      />
      {notice && <Notice kind={notice.kind} onDismiss={() => setNotice(null)}>{notice.text}</Notice>}
      <div className="filter-bar">
        <div className="tabs" aria-label="Compras">
          <Link className={`tab-link ${view === 'orders' ? 'tab-active' : ''}`} to="/purchases/orders">Órdenes</Link>
          <Link className={`tab-link ${view === 'receipts' ? 'tab-active' : ''}`} to="/purchases/receipts">Recepciones</Link>
        </div>
        <button type="button" className="button button-quiet" onClick={() => void load()} disabled={loading}><RefreshCw size={16} className={loading ? 'spin' : ''} /> Actualizar</button>
      </div>
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
      {modal === 'create' && (
        <CreatePurchaseOrderModal
          onClose={() => setModal(null)}
          onCreated={async () => {
            setModal(null)
            setNotice({ kind: 'success', text: 'Orden de compra creada.' })
            await load()
          }}
          onError={reportError}
        />
      )}
      {modal === 'details' && selectedOrder && (
        <Modal title={`Orden #${selectedOrder.id_orden_compra}`} description="Cantidades solicitadas, recibidas y pendientes." onClose={() => setModal(null)}>
          <DataTable
            columns={[
              { key: 'id_producto', label: 'Producto' },
              { key: 'cantidad_solicitada', label: 'Solicitado' },
              { key: 'cantidad_recibida', label: 'Recibido' },
              { key: 'cantidad_pendiente', label: 'Pendiente' },
              { key: 'costo_unitario', label: 'Costo unitario', render: (row) => money.format(Number(row.costo_unitario)) },
            ]}
            rows={lines as unknown as Row[]}
            loading={false}
          />
          {['pendiente', 'recibida_parcial'].includes(String(selectedOrder.estado)) && (
            <div className="form-actions"><button className="button button-primary" onClick={startReceipt}><PackageCheck size={17} /> Registrar recepción</button></div>
          )}
        </Modal>
      )}
      {modal === 'receive' && selectedOrder && (
        <Modal title={`Recepción de orden #${selectedOrder.id_orden_compra}`} description="Ingresa la cantidad total recibida hasta ahora por producto. Repetir los mismos totales no duplica movimientos." onClose={() => !saving && setModal(null)}>
          <form className="receive-list" onSubmit={(event) => void submitReceipt(event)}>
            {lines.map((line) => (
              <label className="receive-line" key={line.id_producto}>
                <span>Producto {line.id_producto}<small>Solicitado {line.cantidad_solicitada} · recibido {line.cantidad_recibida}</small></span>
                <input
                  type="number"
                  name={`received-${line.id_producto}`}
                  min={line.cantidad_recibida}
                  max={line.cantidad_solicitada}
                  defaultValue={line.cantidad_recibida}
                  required
                />
              </label>
            ))}
            <div className="form-actions">
              <button type="button" className="button button-outline" onClick={() => setModal(null)} disabled={saving}>Cancelar</button>
              <button className="button button-primary" disabled={saving}>{saving ? 'Registrando…' : 'Registrar recepción'}</button>
            </div>
          </form>
        </Modal>
      )}
      {modal === 'receiptDetails' && selectedReceipt && (
        <Modal title={`Recepción #${selectedReceipt.id_recepcion}`} description={`Orden #${selectedReceipt.id_orden_compra} · ${displayDate(selectedReceipt.fecha_recepcion)}`} onClose={() => setModal(null)}>
          <DataTable
            columns={[
              { key: 'id_producto', label: 'Producto' },
              { key: 'cantidad_recibida', label: 'Cantidad recibida' },
            ]}
            rows={receiptLines}
          />
        </Modal>
      )}
    </>
  )
}

function CreatePurchaseOrderModal({
  onClose,
  onCreated,
  onError,
}: {
  onClose: () => void
  onCreated: () => Promise<void>
  onError: (message: string) => void
}) {
  const [fields, setFields] = useState<Record<string, string>>({})
  const [availableProducts, setAvailableProducts] = useState<Product[]>([])
  const [products, setProducts] = useState<Array<{ id_producto: number; nombre: string; cantidad_solicitada: number }>>([])
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [loadingProducts, setLoadingProducts] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true
    if (!fields.id_proveedor) {
      setAvailableProducts([])
      return
    }
    setLoadingProducts(true)
    Promise.all([
      api.compras.get<Row[]>('/product-suppliers', { params: { id_proveedor: fields.id_proveedor, estado: 'activo', limit: 100 } }),
      api.catalogo.get<Product[]>('/products', { params: { estado: 'activo', limit: 100 } }),
    ]).then(([relations, catalog]) => {
      if (!active) return
      const productIds = new Set(relations.data.map((relation) => Number(relation.id_producto)))
      setAvailableProducts(catalog.data.filter((product) => productIds.has(product.id_producto)))
    }).catch((error) => {
      if (active) onError(errorMessage(error))
    }).finally(() => {
      if (active) setLoadingProducts(false)
    })
    return () => { active = false }
  }, [fields.id_proveedor, onError])

  function addProduct() {
    const id = Number(productId)
    const count = Number(quantity)
    const product = availableProducts.find((item) => item.id_producto === id)
    if (!product || !Number.isInteger(count) || count <= 0) return
    if (products.some((item) => item.id_producto === id)) return
    setProducts((current) => [...current, { id_producto: id, nombre: product.nombre, cantidad_solicitada: count }])
    setProductId('')
    setQuantity('1')
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!products.length) {
      onError('Agrega al menos un producto asociado al proveedor.')
      return
    }
    setSaving(true)
    try {
      await api.compras.post('/purchase-orders', {
        id_proveedor: Number(fields.id_proveedor),
        id_almacen_destino: Number(fields.id_almacen_destino),
        id_empleado_creador: Number(fields.id_empleado_creador),
        fecha_estimada: fields.fecha_estimada,
        productos: products.map(({ id_producto, cantidad_solicitada }) => ({ id_producto, cantidad_solicitada })),
      })
      await onCreated()
    } catch (error) {
      onError(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title="Nueva orden de compra" description="Los costos se tomarán de la relación producto–proveedor activa." onClose={() => !saving && onClose()}>
      <form className="form-grid" onSubmit={(event) => void submit(event)}>
        {orderFields.map((field) => (
          <FieldInput
            key={field.name}
            field={field}
            value={fields[field.name] ?? ''}
            onChange={(value) => setFields((current) => ({ ...current, [field.name]: value }))}
          />
        ))}
        <div className="form-field form-field-wide">
          <span>Productos de este proveedor</span>
          <div className="inline-product-add">
            <select value={productId} onChange={(event) => setProductId(event.target.value)} disabled={!fields.id_proveedor || loadingProducts}>
              <option value="">{loadingProducts ? 'Cargando…' : 'Selecciona un producto'}</option>
              {availableProducts.map((product) => <option key={product.id_producto} value={product.id_producto}>{product.sku} · {product.nombre}</option>)}
            </select>
            <input aria-label="Cantidad solicitada" type="number" min={1} value={quantity} onChange={(event) => setQuantity(event.target.value)} />
            <button type="button" className="button button-outline" onClick={addProduct}>Agregar</button>
          </div>
          {products.length > 0 && (
            <div className="cart-list">
              {products.map((product) => (
                <div className="cart-line" key={product.id_producto}>
                  <span>{product.nombre}<small>Solicitado: {product.cantidad_solicitada}</small></span>
                  <button type="button" className="icon-button icon-danger" aria-label={`Quitar ${product.nombre}`} onClick={() => setProducts((current) => current.filter((item) => item.id_producto !== product.id_producto))}>×</button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="form-actions">
          <button type="button" className="button button-outline" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="button button-primary" disabled={saving}>{saving ? 'Creando…' : 'Crear orden'}</button>
        </div>
      </form>
    </Modal>
  )
}
