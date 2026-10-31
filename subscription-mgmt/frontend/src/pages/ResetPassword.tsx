import React, { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { authApi } from '../api/client'
import toast from 'react-hot-toast'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const [newPassword, setNewPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authApi.resetPassword(token, newPassword)
      toast.success('Password updated successfully')
      navigate('/login')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to reset password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-6 card">
        <h2 className="text-center text-2xl font-bold text-gray-900">Set New Password</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700">New Password</label>
            <input
              type="password"
              required
              className="input mt-1"
              placeholder="8+ chars, Uppercase, Lowercase, Special"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <button type="submit" disabled={loading} className="w-full btn-primary py-2.5">
            {loading ? 'Updating...' : 'Update Password'}
          </button>
          <div className="text-center text-sm pt-2">
            <Link to="/login" className="text-brand-700 hover:text-brand-800">
              Back to Sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}

