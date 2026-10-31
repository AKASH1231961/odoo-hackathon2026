import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authApi } from '../api/client'
import { useAuthStore } from '../store/auth'
import toast from 'react-hot-toast'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const setTokens = useAuthStore((s) => s.setTokens)
  const setEmailStore = useAuthStore((s) => s.setEmail)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await authApi.login(email, password)
      setTokens(res.data.access_token, res.data.refresh_token)
      setEmailStore(email)
      toast.success('Logged in successfully')
      
      const role = useAuthStore.getState().role
      if (role === 'admin') navigate('/admin')
      else if (role === 'staff') navigate('/staff')
      else navigate('/portal')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 card">
        <div>
          <h2 className="mt-2 text-center text-3xl font-extrabold text-gray-900">Brightloop Software</h2>
          <p className="mt-2 text-center text-sm text-gray-600">Sign in to your account</p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Email Address</label>
              <input
                type="email"
                required
                className="input mt-1"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Password</label>
              <input
                type="password"
                required
                className="input mt-1"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <Link to="/forgot-password" className="text-brand-700 hover:text-brand-800">
              Forgot password?
            </Link>
            <Link to="/register" className="text-brand-700 hover:text-brand-800">
              Create an account
            </Link>
          </div>

          <div>
            <button type="submit" disabled={loading} className="w-full btn-primary py-2.5">
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </div>
        </form>

        <div className="border-t pt-4 text-xs text-gray-500">
          <p className="font-semibold mb-1">Demo Credentials:</p>
          <p>Admin: admin@brightloop.test / Admin@123</p>
          <p>Staff: staff@brightloop.test / Staff@123</p>
          <p>Customer: alice@acme.test / Alice@123</p>
        </div>
      </div>
    </div>
  )
}

