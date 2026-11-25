import { LoaderCircle } from 'lucide-react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import { LoginPage } from '../features/auth/LoginPage'
import { AuditPage } from '../features/audit/AuditPage'
import { HomePage } from '../features/home/HomePage'
import { ResourcePage } from '../features/resources/ResourcePage'
import { InventoryPage } from '../features/operations/InventoryPage'
import { PurchasesPage } from '../features/operations/PurchasesPage'
import { SalesPage } from '../features/operations/SalesPage'
import { PrivateLayout } from '../layouts/PrivateLayout'
import { ReportsPage } from '../features/reports/ReportsPage'

function PrivateRoutes() {
  const { token, ready } = useAuth()
  if (!ready) {
    return <div className="app-loading"><LoaderCircle size={24} className="spin" /><span>Verificando sesiÃ³nâ€¦</span></div>
  }
  if (!token) return <Navigate to="/login" replace />
  return <PrivateLayout />
}


export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<PrivateRoutes />}>
        <Route index element={<HomePage />} />
        <Route path="/identity/employees" element={<ResourcePage resourceKey="employees" />} />
        <Route path="/identity/users" element={<ResourcePage resourceKey="users" />} />
        <Route path="/identity/audit" element={<AuditPage />} />
        <Route path="/catalog/products" element={<ResourcePage resourceKey="products" />} />
        <Route path="/catalog/categories" element={<ResourcePage resourceKey="categories" />} />
        <Route path="/organization/sites" element={<ResourcePage resourceKey="sites" />} />
        <Route path="/organization/warehouses" element={<ResourcePage resourceKey="warehouses" />} />
        <Route path="/purchases/suppliers" element={<ResourcePage resourceKey="suppliers" />} />
        <Route path="/purchases/product-suppliers" element={<ResourcePage resourceKey="productSuppliers" />} />
        <Route path="/purchases/orders" element={<PurchasesPage view="orders" />} />
        <Route path="/purchases/receipts" element={<PurchasesPage view="receipts" />} />
        <Route path="/inventory/stock" element={<InventoryPage view="stock" />} />
        <Route path="/inventory/alerts" element={<InventoryPage view="alerts" />} />
        <Route path="/inventory/transfers" element={<InventoryPage view="transfers" />} />
        <Route path="/sales/customers" element={<ResourcePage resourceKey="customers" />} />
        <Route path="/sales/orders" element={<SalesPage view="orders" />} />
        <Route path="/sales/returns" element={<SalesPage view="returns" />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

