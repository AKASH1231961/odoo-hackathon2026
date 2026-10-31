import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authApi } from '../api/client'
import toast from 'react-hot-toast'

export default function Register() {
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authApi.register(email, password, fullName)
      toast.success('Registration successful! Please login.')
      navigate('/login')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 card">
        <div>
          <h2 className="mt-2 text-center text-3xl font-extrabold text-gray-900">Create an Account</h2>
          <p className="mt-2 text-center text-sm text-gray-600">Join Brightloop Customer Portal</p>
        </div>
        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="text-sm font-medium text-gray-700">Full Name</label>
            <input
              type="text"
              required
              className="input mt-1"
              placeholder="Alice Johnson"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
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
              placeholder="8+ chars, Uppercase, Lowercase, Special"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <p className="text-xs text-gray-500 mt-1">
              Must be 8+ characters and contain uppercase, lowercase, and a special character.
            </p>
          </div>

          <div className="pt-2">
            <button type="submit" disabled={loading} className="w-full btn-primary py-2.5">
              {loading ? 'Registering...' : 'Register'}
            </button>
          </div>

          <div className="text-center text-sm pt-2">
            <Link to="/login" className="text-brand-700 hover:text-brand-800">
              Already have an account? Sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}

