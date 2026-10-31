import React, { useEffect, useState } from 'react'
import { discountsApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function AdminDiscounts() {
  const [discounts, setDiscounts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const [showModal, setShowModal] = useState(false)
  const [name, setName] = useState('')
  const [type, setType] = useState('percentage')
  const [value, setValue] = useState('')
  const [scope, setScope] = useState('subscription')
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0])
  const [maxUses, setMaxUses] = useState('')

  const loadDiscounts = async () => {
    try {
      const res = await discountsApi.list()
      setDiscounts(res.data)
    } catch {
      toast.error('Failed to load discounts')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDiscounts()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await discountsApi.create({
        name,
        type,
        value: Number(value),
        scope,
        start_date: startDate,
        max_uses: maxUses ? Number(maxUses) : undefined,
      })
      toast.success('Discount created')
      setShowModal(false)
      loadDiscounts()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create discount')
    }
  }

  const handleDeactivate = async (id: string) => {
    try {
      await discountsApi.deactivate(id)
      toast.success('Discount deactivated')
      loadDiscounts()
    } catch (err: any) {
      toast.error('Failed to deactivate')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">Discount Rules</h2>
        <button onClick={() => setShowModal(true)} className="btn-primary">Add Discount</button>
      </div>

      <div className="card overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Value</th>
              <th>Scope</th>
              <th>Uses / Max</th>
              <th>Status</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="text-center py-4">Loading...</td></tr>
            ) : discounts.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-4">No discount rules found</td></tr>
            ) : (
              discounts.map((d) => (
                <tr key={d.id}>
                  <td className="font-semibold text-gray-900">{d.name}</td>
                  <td className="capitalize">{d.type}</td>
                  <td>{d.type === 'percentage' ? `${d.value}%` : `$${d.value}`}</td>
                  <td className="capitalize">{d.scope}</td>
                  <td>{d.used_count} / {d.max_uses ?? '∞'}</td>
                  <td>
                    {d.is_active ? <span className="badge-green">Active</span> : <span className="badge-gray">Expired</span>}
                  </td>
                  <td className="text-right">
                    {d.is_active && (
                      <button onClick={() => handleDeactivate(d.id)} className="btn-danger text-xs">Deactivate</button>
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
            <h3 className="text-lg font-bold">New Discount Rule</h3>
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-gray-600">Discount Name</label>
                <input
                  type="text"
                  required
                  className="input mt-1"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-600">Type</label>
                  <select className="input mt-1" value={type} onChange={(e) => setType(e.target.value)}>
                    <option value="percentage">Percentage (%)</option>
                    <option value="fixed">Fixed Amount ($)</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-600">Value</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    className="input mt-1"
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-600">Scope</label>
                  <select className="input mt-1" value={scope} onChange={(e) => setScope(e.target.value)}>
                    <option value="subscription">Subscription</option>
                    <option value="product">Product</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-600">Max Uses</label>
                  <input
                    type="number"
                    className="input mt-1"
                    placeholder="Unlimited if empty"
                    value={maxUses}
                    onChange={(e) => setMaxUses(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Start Date</label>
                <input
                  type="date"
                  required
                  className="input mt-1"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="flex justify-end space-x-2 pt-4">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

