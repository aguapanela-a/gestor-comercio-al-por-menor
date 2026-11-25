import { CreditCard, Eye, Plus, RefreshCw, RotateCcw } from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../../lib/api'
import { displayDate, money } from '../../lib/format'
import { DataTable, type TableColumn } from '../../components/common/DataTable'
import { Modal } from '../../components/common/Modal'
import { Notice } from '../../components/common/Notice'
import { PageHeader } from '../../components/common/PageHeader'
import { StatusBadge } from '../../components/common/StatusBadge'

type Row = Record<string, unknown>
type Product = { id_producto: number; sku: string; nombre: string; precio_lista: number; estado: string }
type OrderLine = { id_pedido: number; id_producto: number; cantidad: number; precio_unitario: number }
type Order = {
  id_pedido: number
  id_sede: number
  id_almacen: number
  id_cliente: number
  id_empleado: number
  fecha_pedido: string
  estado: string
  total_registrado: number
}

export function SalesPage({ view = 'orders' }: { view?: 'orders' | 'returns' }) {
  const [rows, setRows] = useState<Order[]>([])
  const [loading, setLoading] = useState(false)
  const [offset, setOffset] = useState(0)
  const [notice, setNotice] = useState<{ kind: 'error' | 'success' } & { text: string } | null>(null)
  const [modal, setModal] = useState<'create' | 'details' | 'payments' | 'returns' | 'newReturn' | null>(null)
  const [selected, setSelected] = useState<Order | null>(null)
  const [orderLines, setOrderLines] = useState<OrderLine[]>([])
  const [payments, setPayments] = useState<Row[]>([])
  const [returns, setReturns] = useState<Row[]>([])
  const [returnDetails, setReturnDetails] = useState<Row[]>([])
  const [balance, setBalance] = useState<{ total_registrado: number; total_pagado: number; saldo_pendiente: number } | null>(null)
  const [saving, setSaving] = useState(false)
  const reportError = useCallback((text: string) => setNotice({ kind: 'error', text }), [])
  const limit = 20

  const load = useCallback(async () => {
    setLoading(true)
    setNotice(null)
    try {
      const { data } = await api.ventas.get<Order[]>('/orders', { params: { limit, offset } })
      setRows(Array.isArray(data) ? data : [])
    } catch (error) {
      setRows([])
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setLoading(false)
    }
  }, [offset])

  useEffect(() => { void load() }, [load])

  async function showDetails(order: Order) {
    setSelected(order)
    setModal('details')
    try {
      const { data } = await api.ventas.get<OrderLine[]>(`/orders/${order.id_pedido}/details`)
      setOrderLines(data)
    } catch (error) {
      setOrderLines([])
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  async function showPayments(order: Order) {
    setSelected(order)
    setModal('payments')
    try {
      const [paymentsResult, balanceResult] = await Promise.all([
        api.ventas.get<Row[]>(`/orders/${order.id_pedido}/payments`),
        api.ventas.get(`/orders/${order.id_pedido}/balance`),
      ])
      setPayments(paymentsResult.data)
      setBalance(balanceResult.data)
    } catch (error) {
      setPayments([])
      setBalance(null)
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  async function showReturns(order: Order) {
    setSelected(order)
    setModal('returns')
    try {
      const { data } = await api.ventas.get<Row[]>(`/orders/${order.id_pedido}/returns`)
      setReturns(data)
      const { data: lines } = await api.ventas.get<OrderLine[]>(`/orders/${order.id_pedido}/details`)
      setOrderLines(lines)
    } catch (error) {
      setReturns([])
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  async function showReturnDetails(id: unknown) {
    try {
      const { data } = await api.ventas.get<Row[]>(`/returns/${id}/details`)
      setReturnDetails(data)
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  async function resolveReturn(id: unknown, action: 'approve' | 'reject') {
    if (!window.confirm(`¿${action === 'approve' ? 'Aprobar' : 'Rechazar'} la devolución ${id}?`)) return
    try {
      await api.ventas.post(`/returns/${id}/${action}`)
      setNotice({ kind: 'success', text: `Devolución ${action === 'approve' ? 'aprobada' : 'rechazada'}.` })
      if (selected) await showReturns(selected)
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    }
  }

  async function submitPayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected) return
    const formData = new FormData(event.currentTarget)
    setSaving(true)
    try {
      await api.ventas.post(`/orders/${selected.id_pedido}/payments`, {
        valor: String(formData.get('valor') ?? ''),
        medio_pago: String(formData.get('medio_pago') ?? ''),
      })
      const [paymentRows, balanceResult] = await Promise.all([
        api.ventas.get<Row[]>(`/orders/${selected.id_pedido}/payments`),
        api.ventas.get(`/orders/${selected.id_pedido}/balance`),
      ])
      setPayments(paymentRows.data)
      setBalance(balanceResult.data)
      setNotice({ kind: 'success', text: 'Pago registrado.' })
      await load()
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setSaving(false)
    }
  }

  async function submitReturn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected) return
    const formData = new FormData(event.currentTarget)
    const products = orderLines.map((line) => ({
      id_producto: line.id_producto,
      cantidad: Number(formData.get(`return-${line.id_producto}`) ?? 0),
      condicion_producto: String(formData.get(`condition-${line.id_producto}`) ?? 'buen_estado'),
    })).filter((line) => line.cantidad > 0)
    if (!products.length) {
      setNotice({ kind: 'error', text: 'Indica al menos una cantidad mayor a cero.' })
      return
    }
    setSaving(true)
    try {
      await api.ventas.post(`/orders/${selected.id_pedido}/returns`, {
        motivo: String(formData.get('motivo') ?? ''),
        productos: products,
      })
      setModal('returns')
      setNotice({ kind: 'success', text: 'Solicitud de devolución creada.' })
      await showReturns(selected)
    } catch (error) {
      setNotice({ kind: 'error', text: errorMessage(error) })
    } finally {
      setSaving(false)
    }
  }

  const columns: TableColumn<Order>[] = [
    { key: 'id_pedido', label: 'Pedido' },
    { key: 'fecha_pedido', label: 'Fecha', render: (row) => displayDate(row.fecha_pedido) },
    { key: 'id_cliente', label: 'Cliente' },
    { key: 'id_sede', label: 'Sede' },
    { key: 'total_registrado', label: 'Total', render: (row) => money.format(Number(row.total_registrado)) },
    { key: 'estado', label: 'Estado', render: (row) => <StatusBadge value={row.estado} /> },
    {
      key: 'acciones',
      label: 'Acciones',
      render: (row) => (
        <div className="row-actions">
          <button type="button" className="icon-button" title="Detalle" aria-label="Detalle" onClick={() => void showDetails(row)}><Eye size={16} /></button>
          <button type="button" className="icon-button icon-success" title="Pagos" aria-label="Pagos" onClick={() => void showPayments(row)}><CreditCard size={16} /></button>
          <button type="button" className="icon-button" title="Devoluciones" aria-label="Devoluciones" onClick={() => void showReturns(row)}><RotateCcw size={16} /></button>
        </div>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        eyebrow="Ventas"
        title={view === 'orders' ? 'Pedidos' : 'Pagos y devoluciones'}
        description={view === 'orders' ? 'Pedidos registrados por sede y detalle de productos.' : 'Consulta saldos, pagos y solicitudes de devolución desde el pedido.'}
        action={view === 'orders' ? <button className="button button-primary" onClick={() => setModal('create')}><Plus size={17} /> Nuevo pedido</button> : undefined}
      />
      {notice && <Notice kind={notice.kind} onDismiss={() => setNotice(null)}>{notice.text}</Notice>}
      <div className="filter-bar">
        <div className="tabs" aria-label="Ventas">
          <Link className={`tab-link ${view === 'orders' ? 'tab-active' : ''}`} to="/sales/orders">Pedidos</Link>
          <Link className={`tab-link ${view === 'returns' ? 'tab-active' : ''}`} to="/sales/returns">Pagos y devoluciones</Link>
        </div>
        <button type="button" className="button button-quiet" onClick={() => void load()} disabled={loading}><RefreshCw size={16} className={loading ? 'spin' : ''} /> Actualizar</button>
      </div>
      <DataTable
        columns={columns as unknown as TableColumn<Record<string, unknown>>[]}
        rows={rows as unknown as Record<string, unknown>[]}
        loading={loading}
        offset={offset}
        limit={limit}
        canNext={rows.length === limit}
        onPrevious={() => setOffset((current) => Math.max(0, current - limit))}
        onNext={() => setOffset((current) => current + limit)}
      />
      {modal === 'create' && (
        <CreateOrderModal
          onClose={() => setModal(null)}
          onError={reportError}
          onCreated={async () => {
            setModal(null)
            setNotice({ kind: 'success', text: 'Pedido creado. Las existencias consultadas no se reservaron ni descontaron.' })
            await load()
          }}
        />
      )}
      {modal === 'details' && selected && (
        <Modal title={`Pedido #${selected.id_pedido}`} description={`${displayDate(selected.fecha_pedido)} · ${money.format(Number(selected.total_registrado))}`} onClose={() => setModal(null)}>
          <DataTable
            columns={[
              { key: 'id_producto', label: 'Producto' },
              { key: 'cantidad', label: 'Cantidad' },
              { key: 'precio_unitario', label: 'Precio unitario', render: (row) => money.format(Number(row.precio_unitario)) },
              { key: 'subtotal', label: 'Subtotal', render: (row) => money.format(Number(row.cantidad) * Number(row.precio_unitario)) },
            ]}
            rows={orderLines as unknown as Record<string, unknown>[]}
          />
          <div className="form-actions">
            <button type="button" className="button button-outline" onClick={() => void showPayments(selected)}><CreditCard size={16} /> Pagos</button>
            <button type="button" className="button button-primary" onClick={() => void showReturns(selected)}><RotateCcw size={16} /> Devoluciones</button>
          </div>
        </Modal>
      )}
      {modal === 'payments' && selected && (
        <Modal title={`Pagos del pedido #${selected.id_pedido}`} description="El saldo se calcula con pagos aprobados." onClose={() => setModal(null)}>
          {balance && <div className="balance-panel">
            <div><span>Total</span><strong>{money.format(Number(balance.total_registrado))}</strong></div>
            <div><span>Pagado</span><strong>{money.format(Number(balance.total_pagado))}</strong></div>
            <div><span>Saldo pendiente</span><strong className="balance-due">{money.format(Number(balance.saldo_pendiente))}</strong></div>
          </div>}
          <DataTable
            columns={[
              { key: 'fecha_pago', label: 'Fecha', render: (row) => displayDate(row.fecha_pago) },
              { key: 'valor', label: 'Valor', render: (row) => money.format(Number(row.valor)) },
              { key: 'medio_pago', label: 'Medio' },
              { key: 'estado', label: 'Estado', render: (row) => <StatusBadge value={row.estado} /> },
            ]}
            rows={payments}
            emptyMessage="Este pedido no tiene pagos registrados."
          />
          {selected.estado !== 'cancelado' && Number(balance?.saldo_pendiente ?? 0) > 0 && (
            <form className="form-grid payment-form" onSubmit={(event) => void submitPayment(event)}>
              <label className="form-field"><span>Valor del pago</span><input type="number" name="valor" min="0.01" max={balance?.saldo_pendiente} step="0.01" required /></label>
              <label className="form-field"><span>Medio de pago</span><select name="medio_pago" required defaultValue=""><option value="" disabled>Selecciona</option><option value="efectivo">Efectivo</option><option value="tarjeta_credito">Tarjeta de crédito</option><option value="tarjeta_debito">Tarjeta débito</option><option value="transferencia">Transferencia</option></select></label>
              <div className="form-actions form-field-wide"><button className="button button-primary" disabled={saving}>{saving ? 'Registrando…' : 'Registrar pago'}</button></div>
            </form>
          )}
        </Modal>
      )}
      {modal === 'returns' && selected && (
        <Modal title={`Devoluciones del pedido #${selected.id_pedido}`} description="Las solicitudes pendientes también se consideran al validar cantidades disponibles." onClose={() => setModal(null)}>
          {returns.map((item) => (
            <div className="return-row" key={String(item.id_devolucion)}>
              <div><strong>Devolución #{String(item.id_devolucion)}</strong><small>{String(item.motivo ?? 'Sin motivo')} · {displayDate(item.fecha_solicitud)}</small></div>
              <StatusBadge value={item.estado} />
              <button type="button" className="text-button" onClick={() => void showReturnDetails(item.id_devolucion)}>Detalle</button>
              {item.estado === 'pendiente' && (
                <>
                  <button type="button" className="text-button text-success" onClick={() => void resolveReturn(item.id_devolucion, 'approve')}>Aprobar</button>
                  <button type="button" className="text-button text-danger" onClick={() => void resolveReturn(item.id_devolucion, 'reject')}>Rechazar</button>
                </>
              )}
            </div>
          ))}
          {returnDetails.length > 0 && (
            <DataTable columns={[
              { key: 'id_producto', label: 'Producto' },
              { key: 'cantidad', label: 'Cantidad' },
              { key: 'condicion_producto', label: 'Condición' },
            ]} rows={returnDetails} />
          )}
          {['completado', 'devolucion'].includes(selected.estado) && <div className="form-actions"><button type="button" className="button button-primary" onClick={() => setModal('newReturn')}><Plus size={16} /> Solicitar devolución</button></div>}
        </Modal>
      )}
      {modal === 'newReturn' && selected && (
        <Modal title={`Solicitar devolución · Pedido #${selected.id_pedido}`} description="Indica solo los productos y cantidades que se van a devolver." onClose={() => !saving && setModal('returns')}>
          <form className="form-grid" onSubmit={(event) => void submitReturn(event)}>
            <label className="form-field form-field-wide"><span>Motivo</span><textarea name="motivo" required maxLength={200} rows={2} /></label>
            {orderLines.map((line) => (
              <div className="return-input-line form-field-wide" key={line.id_producto}>
                <label className="form-field"><span>Producto {line.id_producto} · vendido {line.cantidad}</span><input name={`return-${line.id_producto}`} type="number" min={0} max={line.cantidad} defaultValue={0} /></label>
                <label className="form-field"><span>Condición</span><select name={`condition-${line.id_producto}`} defaultValue="buen_estado"><option value="buen_estado">Buen estado</option><option value="defectuoso">Defectuoso</option><option value="empaque_abierto">Empaque abierto</option></select></label>
              </div>
            ))}
            <div className="form-actions"><button type="button" className="button button-outline" onClick={() => setModal('returns')} disabled={saving}>Cancelar</button><button className="button button-primary" disabled={saving}>{saving ? 'Enviando…' : 'Enviar solicitud'}</button></div>
          </form>
        </Modal>
      )}
    </>
  )
}

function CreateOrderModal({
  onClose,
  onCreated,
  onError,
}: {
  onClose: () => void
  onCreated: () => Promise<void>
  onError: (message: string) => void
}) {
  const [sites, setSites] = useState<Row[]>([])
  const [warehouses, setWarehouses] = useState<Row[]>([])
  const [employees, setEmployees] = useState<Row[]>([])
  const [customers, setCustomers] = useState<Row[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [site, setSite] = useState('')
  const [warehouse, setWarehouse] = useState('')
  const [customer, setCustomer] = useState('')
  const [employee, setEmployee] = useState('')
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [cart, setCart] = useState<Array<{ id_producto: number; nombre: string; precio_unitario: number; cantidad: number }>>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true
    Promise.all([
      api.organizacion.get<Row[]>('/sedes', { params: { limit: 100 } }),
      api.organizacion.get<Row[]>('/warehouses', { params: { limit: 100, estado: 'activo' } }),
      api.identidad.get<Row[]>('/employees', { params: { limit: 100, estado: 'activo' } }),
      api.ventas.get<Row[]>('/customers', { params: { limit: 100, estado: 'activo' } }),
      api.catalogo.get<Product[]>('/products', { params: { limit: 100, estado: 'activo' } }),
    ]).then(([sitesResult, warehouseResult, employeeResult, customerResult, productResult]) => {
      if (!active) return
      setSites(sitesResult.data)
      setWarehouses(warehouseResult.data)
      setEmployees(employeeResult.data)
      setCustomers(customerResult.data)
      setProducts(productResult.data)
    }).catch((error) => { if (active) onError(errorMessage(error)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [onError])

  const availableWarehouses = warehouses.filter((item) => Number(item.id_sede) === Number(site))
  const availableEmployees = employees.filter((item) => Number(item.id_sede) === Number(site))

  function addProduct() {
    const product = products.find((item) => item.id_producto === Number(productId))
    const count = Number(quantity)
    if (!product || !Number.isInteger(count) || count <= 0 || cart.some((item) => item.id_producto === product.id_producto)) return
    setCart((current) => [...current, {
      id_producto: product.id_producto,
      nombre: product.nombre,
      precio_unitario: Number(product.precio_lista),
      cantidad: count,
    }])
    setProductId('')
    setQuantity('1')
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!cart.length) {
      onError('Agrega por lo menos un producto al pedido.')
      return
    }
    if (!site || !warehouse || !customer || !employee) {
      onError('Completa sede, almacén, cliente y empleado.')
      return
    }
    setSaving(true)
    try {
      for (const product of cart) {
        const { data } = await api.inventarios.get<Row[]>('/stock', {
          params: { id_almacen: Number(warehouse), id_producto: product.id_producto, limit: 100 },
        })
        const stock = data.find((item) => Number(item.id_almacen) === Number(warehouse) && Number(item.id_producto) === product.id_producto)
        if (!stock || Number(stock.existencia_actual) < product.cantidad) {
          throw new Error(`Existencias insuficientes para ${product.nombre}.`)
        }
      }
      await api.ventas.post('/orders', {
        id_sede: Number(site),
        id_almacen: Number(warehouse),
        id_cliente: Number(customer),
        id_empleado: Number(employee),
        productos: cart.map(({ id_producto, cantidad }) => ({ id_producto, cantidad })),
      })
      await onCreated()
    } catch (error) {
      onError(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  const total = cart.reduce((sum, item) => sum + item.precio_unitario * item.cantidad, 0)
  return (
    <Modal title="Nuevo pedido" description="Los precios se toman de Catálogo y la existencia se valida antes de enviar." onClose={() => !saving && onClose()}>
      {loading ? <div className="loading-inline">Cargando datos de venta…</div> : (
        <form className="form-grid" onSubmit={(event) => void submit(event)}>
          <label className="form-field"><span>Sede</span><select required value={site} onChange={(event) => { setSite(event.target.value); setWarehouse(''); setEmployee('') }}><option value="">Selecciona</option>{sites.map((item) => <option key={String(item.id_sede)} value={String(item.id_sede)}>{String(item.nombre)}</option>)}</select></label>
          <label className="form-field"><span>Almacén</span><select required value={warehouse} onChange={(event) => setWarehouse(event.target.value)}><option value="">Selecciona</option>{availableWarehouses.map((item) => <option key={String(item.id_almacen)} value={String(item.id_almacen)}>{String(item.nombre)}</option>)}</select></label>
          <label className="form-field"><span>Cliente</span><select required value={customer} onChange={(event) => setCustomer(event.target.value)}><option value="">Selecciona</option>{customers.map((item) => <option key={String(item.id_cliente)} value={String(item.id_cliente)}>{String(item.nombre_completo)} · {String(item.num_documento)}</option>)}</select></label>
          <label className="form-field"><span>Empleado</span><select required value={employee} onChange={(event) => setEmployee(event.target.value)}><option value="">Selecciona</option>{availableEmployees.map((item) => <option key={String(item.id_empleado)} value={String(item.id_empleado)}>{String(item.nombre_completo)}</option>)}</select></label>
          <div className="form-field form-field-wide">
            <span>Productos</span>
            <div className="inline-product-add"><select value={productId} onChange={(event) => setProductId(event.target.value)}><option value="">Selecciona producto</option>{products.map((item) => <option key={item.id_producto} value={item.id_producto}>{item.sku} · {item.nombre} · {money.format(Number(item.precio_lista))}</option>)}</select><input aria-label="Cantidad" type="number" min={1} value={quantity} onChange={(event) => setQuantity(event.target.value)} /><button type="button" className="button button-outline" onClick={addProduct}>Agregar</button></div>
            {cart.map((item) => <div className="cart-line" key={item.id_producto}><span>{item.nombre}<small>{item.cantidad} × {money.format(item.precio_unitario)}</small></span><strong>{money.format(item.cantidad * item.precio_unitario)}</strong><button type="button" className="icon-button icon-danger" aria-label={`Quitar ${item.nombre}`} onClick={() => setCart((current) => current.filter((entry) => entry.id_producto !== item.id_producto))}>×</button></div>)}
            {cart.length > 0 && <div className="cart-total"><span>Total calculado</span><strong>{money.format(total)}</strong></div>}
          </div>
          <div className="form-actions"><button type="button" className="button button-outline" onClick={onClose}>Cancelar</button><button className="button button-primary" disabled={saving}>{saving ? 'Creando…' : 'Crear pedido'}</button></div>
        </form>
      )}
    </Modal>
  )
}
