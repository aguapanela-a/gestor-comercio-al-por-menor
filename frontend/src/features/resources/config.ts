import type { ServiceName } from '../../lib/api'
import type { FieldDefinition, SelectOption } from '../../components/common/FieldInput'
import type { TableColumn } from '../../components/common/DataTable'

export interface ResourceDefinition {
  service: ServiceName
  path: string
  idField: string
  title: string
  description: string
  singular: string
  columns: TableColumn<Record<string, unknown>>[]
  fields: FieldDefinition[]
  filters?: FieldDefinition[]
  searchParam?: string
  searchLabel?: string
  create?: boolean
  update?: boolean
  deactivate?: boolean
  createPath?: string
  createPathFromPayload?: (payload: Record<string, unknown>) => string
  createMethod?: 'post' | 'put'
  rowPath?: (row: Record<string, unknown>) => string
  updatePath?: (row: Record<string, unknown>) => string
  deactivatePath?: (row: Record<string, unknown>) => string
  updateMethod?: 'patch' | 'put'
  limit?: number
  actions?: boolean
}

const stateOptions: SelectOption[] = [
  { value: 'activo', label: 'Activo' },
  { value: 'inactivo', label: 'Inactivo' },
]

const siteTypes: SelectOption[] = [
  { value: 'comercial', label: 'Comercial' },
  { value: 'distribucion', label: 'Distribución' },
]

const warehouseTypes: SelectOption[] = [
  { value: 'principal', label: 'Principal' },
  { value: 'venta', label: 'Venta' },
  { value: 'recepcion', label: 'Recepción' },
]

const stateField: FieldDefinition = {
  name: 'estado',
  label: 'Estado',
  type: 'select',
  options: stateOptions,
}

export const resourceDefinitions: Record<string, ResourceDefinition> = {
  employees: {
    service: 'identidad',
    path: '/employees',
    idField: 'id_empleado',
    title: 'Empleados',
    description: 'Directorio de personal registrado en Identidad.',
    singular: 'empleado',
    searchParam: 'q',
    searchLabel: 'Buscar empleado',
    columns: [
      { key: 'id_empleado', label: 'ID' },
      { key: 'nombre_completo', label: 'Nombre' },
      { key: 'num_documento', label: 'Documento' },
      { key: 'cargo', label: 'Cargo' },
      { key: 'id_sede', label: 'Sede' },
      { key: 'estado', label: 'Estado' },
    ],
    fields: [
      { name: 'id_sede', label: 'Sede', type: 'select', required: true, remote: { service: 'organizacion', path: '/sedes', value: 'id_sede', label: 'nombre', params: { estado: 'activo' } } },
      { name: 'num_documento', label: 'Número de documento', required: true, maxLength: 20 },
      { name: 'nombre_completo', label: 'Nombre completo', required: true, maxLength: 120 },
      { name: 'cargo', label: 'Cargo', required: true, maxLength: 60 },
      { name: 'correo', label: 'Correo electrónico', type: 'email', maxLength: 100 },
      stateField,
    ],
    filters: [
      { name: 'id_sede', label: 'Sede', type: 'select', remote: { service: 'organizacion', path: '/sedes', value: 'id_sede', label: 'nombre', params: { estado: 'activo' } } },
      stateField,
    ],
    create: true,
    update: true,
    deactivate: true,
  },
  users: {
    service: 'identidad',
    path: '/users',
    idField: 'id_usuario',
    title: 'Usuarios',
    description: 'Cuentas de acceso vinculadas a empleados.',
    singular: 'usuario',
    columns: [
      { key: 'id_usuario', label: 'ID' },
      { key: 'nombre_usuario', label: 'Usuario' },
      { key: 'id_empleado', label: 'ID empleado' },
      { key: 'fecha_creacion', label: 'Creado' },
      { key: 'estado', label: 'Estado' },
    ],
    fields: [
      { name: 'id_empleado', label: 'Empleado', type: 'select', required: true, createOnly: true, remote: { service: 'identidad', path: '/employees', value: 'id_empleado', label: 'nombre_completo', params: { estado: 'activo' } } },
      { name: 'nombre_usuario', label: 'Nombre de usuario', required: true, maxLength: 50 },
      { name: 'password', label: 'Contraseña inicial', type: 'password', required: true, createOnly: true, maxLength: 128 },
      stateField,
    ],
    filters: [
      { name: 'id_empleado', label: 'Empleado', type: 'select', remote: { service: 'identidad', path: '/employees', value: 'id_empleado', label: 'nombre_completo', params: { estado: 'activo' } } },
      stateField,
    ],
    create: true,
    update: true,
    deactivate: true,
    updateMethod: 'patch',
  },
  categories: {
    service: 'catalogo',
    path: '/categories',
    idField: 'id_categoria',
    title: 'Categorías',
    description: 'Clasificación de productos del catálogo.',
    singular: 'categoría',
    searchParam: 'q',
    searchLabel: 'Buscar categoría',
    columns: [
      { key: 'id_categoria', label: 'ID' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'descripcion', label: 'Descripción' },
      { key: 'estado', label: 'Estado' },
    ],
    fields: [
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 80 },
      { name: 'descripcion', label: 'Descripción', type: 'textarea', maxLength: 200 },
      stateField,
    ],
    filters: [stateField],
    create: true,
    update: true,
    deactivate: true,
  },
  products: {
    service: 'catalogo',
    path: '/products',
    idField: 'id_producto',
    title: 'Productos',
    description: 'Productos, precios de lista y disponibilidad del catálogo.',
    singular: 'producto',
    searchParam: 'q',
    searchLabel: 'Buscar por SKU o nombre',
    columns: [
      { key: 'sku', label: 'SKU' },
      { key: 'nombre', label: 'Producto' },
      { key: 'id_categoria', label: 'Categoría' },
      { key: 'precio_lista', label: 'Precio' },
      { key: 'unidad_medida', label: 'Unidad' },
      { key: 'estado', label: 'Estado' },
    ],
    fields: [
      { name: 'sku', label: 'SKU', required: true, maxLength: 30 },
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 120 },
      { name: 'id_categoria', label: 'Categoría', type: 'select', required: true, remote: { service: 'catalogo', path: '/categories', value: 'id_categoria', label: 'nombre', params: { estado: 'activo' } } },
      { name: 'unidad_medida', label: 'Unidad de medida', required: true, maxLength: 20 },
      { name: 'precio_lista', label: 'Precio de lista', type: 'number', required: true, min: 0 },
      stateField,
    ],
    filters: [
      { name: 'id_categoria', label: 'Categoría', type: 'select', remote: { service: 'catalogo', path: '/categories', value: 'id_categoria', label: 'nombre', params: { estado: 'activo' } } },
      stateField,
    ],
    create: true,
    update: true,
    deactivate: true,
  },
  sites: {
    service: 'organizacion',
    path: '/sedes',
    idField: 'id_sede',
    title: 'Sedes',
    description: 'Ubicaciones comerciales y centros de distribución.',
    singular: 'sede',
    columns: [
      { key: 'id_sede', label: 'ID' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'ciudad', label: 'Ciudad' },
      { key: 'tipo_sede', label: 'Tipo' },
      { key: 'estado', label: 'Estado' },
    ],
    fields: [
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 80 },
      { name: 'ciudad', label: 'Ciudad', required: true, maxLength: 60 },
      { name: 'direccion', label: 'Dirección', required: true, maxLength: 120 },
      { name: 'tipo_sede', label: 'Tipo de sede', type: 'select', required: true, options: siteTypes },
      stateField,
    ],
    filters: [
      { name: 'tipo_sede', label: 'Tipo de sede', type: 'select', options: siteTypes },
      stateField,
    ],
    create: true,
    update: true,
    deactivate: true,
  },
  warehouses: {
    service: 'organizacion',
    path: '/warehouses',
    idField: 'id_almacen',
    title: 'Almacenes',
    description: 'Almacenes asociados a sedes.',
    singular: 'almacén',
    columns: [
      { key: 'id_almacen', label: 'ID' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'id_sede', label: 'Sede' },
      { key: 'tipo_almacen', label: 'Tipo' },
      { key: 'estado', label: 'Estado' },
    ],
    fields: [
      { name: 'id_sede', label: 'Sede', type: 'select', required: true, remote: { service: 'organizacion', path: '/sedes', value: 'id_sede', label: 'nombre', params: { estado: 'activo' } } },
      { name: 'nombre', label: 'Nombre', required: true, maxLength: 80 },
      { name: 'tipo_almacen', label: 'Tipo de almacén', type: 'select', required: true, options: warehouseTypes },
      stateField,
    ],
    filters: [
      { name: 'id_sede', label: 'Sede', type: 'select', remote: { service: 'organizacion', path: '/sedes', value: 'id_sede', label: 'nombre', params: { estado: 'activo' } } },
      { name: 'tipo_almacen', label: 'Tipo de almacén', type: 'select', options: warehouseTypes },
      stateField,
    ],
    create: true,
    update: true,
    deactivate: true,
  },
  suppliers: {
    service: 'compras',
    path: '/suppliers',
    idField: 'id_proveedor',
    title: 'Proveedores',
    description: 'Empresas proveedoras habilitadas para abastecimiento.',
    singular: 'proveedor',
    searchParam: 'q',
    searchLabel: 'Buscar por identificación o razón social',
    columns: [
      { key: 'identificacion', label: 'Identificación' },
      { key: 'razon_social', label: 'Razón social' },
      { key: 'ciudad', label: 'Ciudad' },
      { key: 'correo', label: 'Correo' },
      { key: 'telefono', label: 'Teléfono' },
      { key: 'estado', label: 'Estado' },
    ],
    fields: [
      { name: 'identificacion', label: 'Identificación', required: true, maxLength: 20 },
      { name: 'razon_social', label: 'Razón social', required: true, maxLength: 100 },
      { name: 'ciudad', label: 'Ciudad', required: true, maxLength: 50 },
      { name: 'correo', label: 'Correo electrónico', type: 'email', required: true, maxLength: 100 },
      { name: 'telefono', label: 'Teléfono', required: true, maxLength: 20 },
      stateField,
    ],
    filters: [stateField],
    create: true,
    update: true,
    deactivate: true,
  },
  productSuppliers: {
    service: 'compras',
    path: '/product-suppliers',
    idField: 'id_producto',
    title: 'Productos por proveedor',
    description: 'Costos de referencia y plazo acordado por producto y proveedor.',
    singular: 'relación',
    columns: [
      { key: 'id_producto', label: 'ID producto' },
      { key: 'id_proveedor', label: 'ID proveedor' },
      { key: 'costo_referencia', label: 'Costo de referencia' },
      { key: 'plazo_entrega_dias', label: 'Plazo (días)' },
      { key: 'estado', label: 'Estado' },
    ],
    fields: [
      { name: 'id_producto', label: 'Producto', type: 'select', required: true, createOnly: true, remote: { service: 'catalogo', path: '/products', value: 'id_producto', label: 'nombre', params: { estado: 'activo' } } },
      { name: 'id_proveedor', label: 'Proveedor', type: 'select', required: true, createOnly: true, remote: { service: 'compras', path: '/suppliers', value: 'id_proveedor', label: 'razon_social', params: { estado: 'activo' } } },
      { name: 'costo_referencia', label: 'Costo de referencia', type: 'number', required: true, min: 0 },
      { name: 'plazo_entrega_dias', label: 'Plazo de entrega (días)', type: 'number', required: true, min: 0 },
      stateField,
    ],
    filters: [
      { name: 'id_proveedor', label: 'Proveedor', type: 'select', remote: { service: 'compras', path: '/suppliers', value: 'id_proveedor', label: 'razon_social', params: { estado: 'activo' } } },
      { name: 'id_producto', label: 'Producto', type: 'select', remote: { service: 'catalogo', path: '/products', value: 'id_producto', label: 'nombre', params: { estado: 'activo' } } },
      stateField,
    ],
    create: true,
    update: true,
    deactivate: true,
    createMethod: 'put',
    createPathFromPayload: (payload) => `/product-suppliers/${payload.id_producto}/${payload.id_proveedor}`,
    rowPath: (row) => `/product-suppliers/${row.id_producto}/${row.id_proveedor}`,
    updatePath: (row) => `/product-suppliers/${row.id_producto}/${row.id_proveedor}`,
    deactivatePath: (row) => `/product-suppliers/${row.id_producto}/${row.id_proveedor}`,
    updateMethod: 'put',
  },
  customers: {
    service: 'ventas',
    path: '/customers',
    idField: 'id_cliente',
    title: 'Clientes',
    description: 'Directorio de clientes para pedidos y facturación.',
    singular: 'cliente',
    searchParam: 'q',
    searchLabel: 'Buscar cliente',
    columns: [
      { key: 'num_documento', label: 'Documento' },
      { key: 'nombre_completo', label: 'Nombre' },
      { key: 'tipo_documento', label: 'Tipo doc.' },
      { key: 'correo', label: 'Correo' },
      { key: 'telefono', label: 'Teléfono' },
      { key: 'estado', label: 'Estado' },
    ],
    fields: [
      { name: 'tipo_documento', label: 'Tipo de documento', required: true, maxLength: 5 },
      { name: 'num_documento', label: 'Número de documento', required: true, maxLength: 20 },
      { name: 'nombre_completo', label: 'Nombre completo', required: true, maxLength: 120 },
      { name: 'correo', label: 'Correo electrónico', type: 'email', required: true, maxLength: 100 },
      { name: 'telefono', label: 'Teléfono', required: true, maxLength: 20 },
      stateField,
    ],
    filters: [stateField],
    create: true,
    update: true,
    deactivate: true,
  },
}
