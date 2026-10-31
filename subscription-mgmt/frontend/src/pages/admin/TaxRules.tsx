import React, { useEffect, useState } from 'react'
import { taxRulesApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function AdminTaxRules() {
  const [taxes, setTaxes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const [showModal, setShowModal] = useState(false)
  const [name, setName] = useState('')
  const [rate, setRate] = useState('')
  const [appliesTo, setAppliesTo] = useState('all')

  const loadTaxes = async () => {
    try {
      const res = await taxRulesApi.list()
      setTaxes(res.data)
    } catch {
      toast.error('Failed to load tax rules')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTaxes()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await taxRulesApi.create({
        name,
        rate: Number(rate) / 100, // input is percentage e.g. 18 -> 0.18
        applies_to: appliesTo,
      })
      toast.success('Tax rule created')
      setShowModal(false)
      loadTaxes()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create tax rule')
    }
  }

  const handleDeactivate = async (id: string) => {
    try {
      await taxRulesApi.deactivate(id)
      toast.success('Tax rule deactivated')
      loadTaxes()
    } catch {
      toast.error('Failed to deactivate')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">Tax Rules</h2>
        <button onClick={() => setShowModal(true)} className="btn-primary">Add Tax Rule</button>
      </div>

      <div className="card overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Rate (%)</th>
              <th>Applies To</th>
              <th>Status</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="text-center py-4">Loading...</td></tr>
            ) : taxes.length === 0 ? (
              <tr><td colSpan={5} className="text-center py-4">No active tax rules</td></tr>
            ) : (
              taxes.map((t) => (
                <tr key={t.id}>
                  <td className="font-semibold text-gray-900">{t.name}</td>
                  <td>{(Number(t.rate) * 100).toFixed(2)}%</td>
                  <td className="capitalize">{t.applies_to}</td>
                  <td>
                    {t.is_active ? <span className="badge-green">Active</span> : <span className="badge-gray">Inactive</span>}
                  </td>
                  <td className="text-right">
                    {t.is_active && (
                      <button onClick={() => handleDeactivate(t.id)} className="btn-danger text-xs">Deactivate</button>
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
            <h3 className="text-lg font-bold">New Tax Rule</h3>
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-gray-600">Rule Name</label>
                <input
                  type="text"
                  required
                  className="input mt-1"
                  placeholder="e.g. GST 18%"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Rate (%)</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  className="input mt-1"
                  placeholder="18"
                  value={rate}
                  onChange={(e) => setRate(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Applies To</label>
                <select className="input mt-1" value={appliesTo} onChange={(e) => setAppliesTo(e.target.value)}>
                  <option value="all">Global (All Products & Plans)</option>
                  <option value="product">Specific Product</option>
                  <option value="plan">Specific Plan</option>
                </select>
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

