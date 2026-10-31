import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/auth'

// Auth pages
import Login from './pages/Login'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Register from './pages/Register'

// Admin pages
import AdminLayout from './pages/admin/Layout'
import AdminDashboard from './pages/admin/Dashboard'
import AdminProducts from './pages/admin/Products'
import AdminPlans from './pages/admin/Plans'
import AdminSubscriptions from './pages/admin/Subscriptions'
import AdminInvoices from './pages/admin/Invoices'
import AdminPayments from './pages/admin/Payments'
import AdminDiscounts from './pages/admin/Discounts'
import AdminTaxRules from './pages/admin/TaxRules'
import AdminUsers from './pages/admin/Users'
import AdminReports from './pages/admin/Reports'

// Staff pages
import StaffLayout from './pages/staff/Layout'
import StaffSubscriptions from './pages/staff/Subscriptions'
import StaffInvoices from './pages/staff/Invoices'
import StaffPayments from './pages/staff/Payments'

// Portal pages
import PortalLayout from './pages/portal/Layout'
import PortalDashboard from './pages/portal/Dashboard'
import PortalSubscriptions from './pages/portal/Subscriptions'
import PortalInvoices from './pages/portal/Invoices'
import PortalProfile from './pages/portal/Profile'

import ProtectedRoute from './components/ProtectedRoute'

export default function App() {
  const role = useAuthStore((s) => s.role)

  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      {/* Admin routes */}
      <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="products" element={<AdminProducts />} />
          <Route path="plans" element={<AdminPlans />} />
          <Route path="subscriptions" element={<AdminSubscriptions />} />
          <Route path="invoices" element={<AdminInvoices />} />
          <Route path="payments" element={<AdminPayments />} />
          <Route path="discounts" element={<AdminDiscounts />} />
          <Route path="tax-rules" element={<AdminTaxRules />} />
          <Route path="reports" element={<AdminReports />} />
        </Route>
      </Route>

      {/* Staff routes */}
      <Route element={<ProtectedRoute allowedRoles={['admin', 'staff']} />}>
        <Route path="/staff" element={<StaffLayout />}>
          <Route index element={<StaffSubscriptions />} />
          <Route path="subscriptions" element={<StaffSubscriptions />} />
          <Route path="invoices" element={<StaffInvoices />} />
          <Route path="payments" element={<StaffPayments />} />
        </Route>
      </Route>

      {/* Customer portal */}
      <Route element={<ProtectedRoute allowedRoles={['customer']} />}>
        <Route path="/portal" element={<PortalLayout />}>
          <Route index element={<PortalDashboard />} />
          <Route path="subscriptions" element={<PortalSubscriptions />} />
          <Route path="invoices" element={<PortalInvoices />} />
          <Route path="profile" element={<PortalProfile />} />
        </Route>
      </Route>

      {/* Root redirect based on role */}
      <Route
        path="/"
        element={
          role === 'admin' ? <Navigate to="/admin" replace /> :
          role === 'staff' ? <Navigate to="/staff" replace /> :
          role === 'customer' ? <Navigate to="/portal" replace /> :
          <Navigate to="/login" replace />
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

