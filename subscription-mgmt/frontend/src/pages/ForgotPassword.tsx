import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../api/client'
import toast from 'react-hot-toast'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authApi.forgotPassword(email)
      setSubmitted(true)
      toast.success('Reset email requested')
    } catch (err: any) {
      toast.error('Failed to request reset')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-6 card">
        <h2 className="text-center text-2xl font-bold text-gray-900">Reset Password</h2>
        {submitted ? (
          <div className="text-center space-y-4">
            <p className="text-sm text-gray-600">
              If an account with that email exists, we've sent password reset instructions.
            </p>
            <Link to="/login" className="btn-secondary inline-block">Back to Login</Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Account Email</label>
              <input
                type="email"
                required
                className="input mt-1"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <button type="submit" disabled={loading} className="w-full btn-primary py-2.5">
              {loading ? 'Sending...' : 'Send Reset Link'}
            </button>
            <div className="text-center text-sm pt-2">
              <Link to="/login" className="text-brand-700 hover:text-brand-800">
                Back to Sign in
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

