import React from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/auth'

export default function AdminLayout() {
  const logout = useAuthStore((s) => s.logout)
  const email = useAuthStore((s) => s.email)
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navItems = [
    { name: 'Dashboard', path: '/admin' },
    { name: 'Subscriptions', path: '/admin/subscriptions' },
    { name: 'Invoices', path: '/admin/invoices' },
    { name: 'Payments', path: '/admin/payments' },
    { name: 'Products & Variants', path: '/admin/products' },
    { name: 'Billing Plans', path: '/admin/plans' },
    { name: 'Discounts', path: '/admin/discounts' },
    { name: 'Tax Rules', path: '/admin/tax-rules' },
    { name: 'Users & Staff', path: '/admin/users' },
    { name: 'Reports & BI', path: '/admin/reports' },
  ]

  return (
    <div className="min-h-screen flex bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white flex flex-col justify-between">
        <div>
          <div className="p-5 border-b border-gray-800">
            <h1 className="text-xl font-bold tracking-tight text-white">Brightloop Admin</h1>
            <p className="text-xs text-gray-400 mt-1">{email || 'Administrator'}</p>
          </div>
          <nav className="p-3 space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/admin'}
                className={({ isActive }) =>
                  `flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? 'bg-brand-700 text-white'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  }`
                }
              >
                {item.name}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="p-4 border-t border-gray-800">
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center px-4 py-2 text-sm text-red-400 hover:bg-gray-800 rounded-lg transition-colors"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto">
        <header className="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-800">Subscription Operations</h2>
          <span className="badge-blue">System Mode: Production</span>
        </header>
        <main className="p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

