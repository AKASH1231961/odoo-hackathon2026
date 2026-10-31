import React from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/auth'

export default function PortalLayout() {
  const logout = useAuthStore((s) => s.logout)
  const email = useAuthStore((s) => s.email)
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navItems = [
    { name: 'Dashboard', path: '/portal' },
    { name: 'My Subscriptions', path: '/portal/subscriptions' },
    { name: 'My Invoices', path: '/portal/invoices' },
    { name: 'Profile & Settings', path: '/portal/profile' },
  ]

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between h-16 items-center">
          <div className="flex items-center space-x-8">
            <span className="text-xl font-bold text-brand-900">Brightloop Customer Portal</span>
            <nav className="flex space-x-4">
              {navItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/portal'}
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-brand-50 text-brand-700 font-semibold'
                        : 'text-gray-600 hover:text-gray-900'
                    }`
                  }
                >
                  {item.name}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-xs text-gray-500">{email}</span>
            <button onClick={handleLogout} className="btn-secondary text-xs">Sign Out</button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full">
        <Outlet />
      </main>
    </div>
  )
}

