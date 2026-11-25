import {
  ArrowLeftRight,
  Boxes,
  Building2,
  ClipboardList,
  CircleAlert,
  FileBarChart,
  LayoutDashboard,
  Package,
  ShoppingCart,
  Tags,
  Truck,
  Users,
  Warehouse,
  type LucideIcon,
} from 'lucide-react'

export interface NavigationItem {
  label: string
  path: string
  icon: LucideIcon
}

export interface NavigationGroup {
  label: string
  items: NavigationItem[]
}

export const navigationGroups: NavigationGroup[] = [
  { label: 'General', items: [{ label: 'Inicio', path: '/', icon: LayoutDashboard }] },
  {
    label: 'Identidad',
    items: [
      { label: 'Empleados', path: '/identity/employees', icon: Users },
      { label: 'Usuarios', path: '/identity/users', icon: Users },
    ],
  },
  {
    label: 'Catálogo',
    items: [
      { label: 'Productos', path: '/catalog/products', icon: Package },
      { label: 'Categorías', path: '/catalog/categories', icon: Tags },
    ],
  },
  {
    label: 'Organización',
    items: [
      { label: 'Sedes', path: '/organization/sites', icon: Building2 },
      { label: 'Almacenes', path: '/organization/warehouses', icon: Warehouse },
    ],
  },
  {
    label: 'Compras',
    items: [
      { label: 'Proveedores', path: '/purchases/suppliers', icon: Truck },
      { label: 'Productos por proveedor', path: '/purchases/product-suppliers', icon: ClipboardList },
      { label: 'Órdenes de compra', path: '/purchases/orders', icon: ShoppingCart },
      { label: 'Recepciones', path: '/purchases/receipts', icon: ClipboardList },
    ],
  },
  {
    label: 'Inventarios',
    items: [
      { label: 'Existencias', path: '/inventory/stock', icon: Boxes },
      { label: 'Alertas de stock', path: '/inventory/alerts', icon: CircleAlert },
      { label: 'Transferencias', path: '/inventory/transfers', icon: ArrowLeftRight },
    ],
  },
  {
    label: 'Ventas',
    items: [
      { label: 'Clientes', path: '/sales/customers', icon: Users },
      { label: 'Pedidos', path: '/sales/orders', icon: ShoppingCart },
      { label: 'Pagos y devoluciones', path: '/sales/returns', icon: ClipboardList },
    ],
  },
  { label: 'Análisis', items: [{ label: 'Reportes', path: '/reports', icon: FileBarChart }] },
]

export const routeTitles = new Map(
  navigationGroups.flatMap((group) => group.items.map((item) => [item.path, item.label] as const)),
)
