import React, { useEffect, useState } from 'react'
import { portalApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function PortalProfile() {
  const [profile, setProfile] = useState<any>(null)
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    async function loadData() {
      try {
        const res = await portalApi.profile()
        setProfile(res.data)
        setFullName(res.data.full_name || '')
      } catch {
        toast.error('Failed to load profile')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload: any = { full_name: fullName }
      if (password) payload.password = password
      const res = await portalApi.updateProfile(payload)
      setProfile(res.data)
      setPassword('')
      toast.success('Profile updated successfully')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="text-gray-500">Loading profile...</div>

  return (
    <div className="max-w-xl mx-auto card space-y-6">
      <h2 className="text-xl font-bold text-gray-900">Profile & Security</h2>

      <form onSubmit={handleUpdate} className="space-y-4">
        <div>
          <label className="text-sm font-medium text-gray-700">Email Address (Read-only)</label>
          <input
            type="email"
            disabled
            className="input mt-1 bg-gray-100 text-gray-500"
            value={profile?.email || ''}
          />
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700">Full Name</label>
          <input
            type="text"
            required
            className="input mt-1"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700">Change Password (Optional)</label>
          <input
            type="password"
            className="input mt-1"
            placeholder="Leave blank to keep current password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <p className="text-xs text-gray-500 mt-1">
            If changing: 8+ chars with uppercase, lowercase, and special character.
          </p>
        </div>

        <div className="pt-2">
          <button type="submit" disabled={saving} className="btn-primary w-full py-2.5">
            {saving ? 'Saving Changes...' : 'Save Profile'}
          </button>
        </div>
      </form>
    </div>
  )
}

