import React, { useEffect, useState } from 'react'
import { usersApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function AdminUsers() {
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const [showModal, setShowModal] = useState(false)
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('staff')

  const loadUsers = async () => {
    try {
      const res = await usersApi.list()
      setUsers(res.data)
    } catch {
      toast.error('Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await usersApi.createStaff({
        email,
        full_name: fullName,
        password,
        role,
      })
      toast.success('Staff user created')
      setShowModal(false)
      setEmail('')
      setPassword('')
      loadUsers()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create user')
    }
  }

  const handleDeactivate = async (id: string) => {
    try {
      await usersApi.deactivate(id)
      toast.success('User deactivated')
      loadUsers()
    } catch {
      toast.error('Failed to deactivate')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">User Management</h2>
        <button onClick={() => setShowModal(true)} className="btn-primary">Create Staff Member</button>
      </div>

      <div className="card overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>Full Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Joined Date</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-4">Loading...</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-4">No users found</td></tr>
            ) : (
              users.map((u) => (
                <tr key={u.id}>
                  <td className="font-semibold text-gray-900">{u.full_name || '—'}</td>
                  <td>{u.email}</td>
                  <td>
                    <span className={`badge uppercase ${u.role === 'admin' ? 'badge-blue' : u.role === 'staff' ? 'badge-yellow' : 'badge-gray'}`}>
                      {u.role}
                    </span>
                  </td>
                  <td>
                    {u.is_active ? <span className="badge-green">Active</span> : <span className="badge-red">Disabled</span>}
                  </td>
                  <td>{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="text-right">
                    {u.is_active && u.role !== 'admin' && (
                      <button onClick={() => handleDeactivate(u.id)} className="btn-danger text-xs">Deactivate</button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold">Create Staff Account</h3>
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-gray-600">Full Name</label>
                <input
                  type="text"
                  required
                  className="input mt-1"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Email Address</label>
                <input
                  type="email"
                  required
                  className="input mt-1"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Role</label>
                <select className="input mt-1" value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="staff">Staff Member</option>
                  <option value="admin">Administrator</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Password</label>
                <input
                  type="password"
                  required
                  className="input mt-1"
                  placeholder="8+ chars, Uppercase, Lowercase, Special"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <div className="flex justify-end space-x-2 pt-4">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">Create User</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

