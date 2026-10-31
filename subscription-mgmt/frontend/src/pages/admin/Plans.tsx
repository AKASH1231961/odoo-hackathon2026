import React, { useEffect, useState } from 'react'
import { plansApi, productsApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function AdminPlans() {
  const [plans, setPlans] = useState<any[]>([])
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const [showModal, setShowModal] = useState(false)
  const [name, setName] = useState('')
  const [productId, setProductId] = useState('')
  const [interval, setInterval] = useState('monthly')
  const [price, setPrice] = useState('')
  const [minQty, setMinQty] = useState(1)

  const loadData = async () => {
    try {
      const [plansRes, prodsRes] = await Promise.all([
        plansApi.list(),
        productsApi.list(),
      ])
      setPlans(plansRes.data)
      setProducts(prodsRes.data)
      if (prodsRes.data.length > 0) setProductId(prodsRes.data[0].id)
    } catch {
      toast.error('Failed to load plans')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await plansApi.create({
        name,
        product_id: productId,
        billing_interval: interval,
        price: Number(price),
        min_quantity: Number(minQty),
      })
      toast.success('Plan created')
      setShowModal(false)
      setName('')
      setPrice('')
      loadData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create plan')
    }
  }

  const handleClose = async (id: string) => {
    try {
      await plansApi.close(id)
      toast.success('Plan closed')
      loadData()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to close plan')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">Subscription Plans</h2>
        <button onClick={() => setShowModal(true)} className="btn-primary">Add Plan</button>
      </div>

      <div className="card overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>Plan Name</th>
              <th>Interval</th>
              <th>Price</th>
              <th>Min Quantity</th>
              <th>Can Pause</th>
              <th>Status</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="text-center py-4">Loading...</td></tr>
            ) : plans.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-4">No plans found</td></tr>
            ) : (
              plans.map((p) => (
                <tr key={p.id}>
                  <td className="font-semibold text-gray-900">{p.name}</td>
                  <td className="capitalize">{p.billing_interval}</td>
                  <td className="font-semibold">${Number(p.price).toFixed(2)}</td>
                  <td>{p.min_quantity}</td>
                  <td>{p.can_pause ? 'Yes' : 'No'}</td>
                  <td>
                    {p.is_active ? <span className="badge-green">Active</span> : <span className="badge-gray">Closed</span>}
                  </td>
                  <td className="text-right">
                    {p.is_active && (
                      <button onClick={() => handleClose(p.id)} className="btn-danger text-xs">Close Plan</button>
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
            <h3 className="text-lg font-bold">New Billing Plan</h3>
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-gray-600">Plan Name</label>
                <input
                  type="text"
                  required
                  className="input mt-1"
                  placeholder="e.g. ERP Monthly Starter"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Base Product</label>
                <select className="input mt-1" value={productId} onChange={(e) => setProductId(e.target.value)}>
                  {products.map((prod) => (
                    <option key={prod.id} value={prod.id}>{prod.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-600">Billing Interval</label>
                  <select className="input mt-1" value={interval} onChange={(e) => setInterval(e.target.value)}>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="yearly">Yearly</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-600">Price ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    className="input mt-1"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Minimum Quantity</label>
                <input
                  type="number"
                  min="1"
                  required
                  className="input mt-1"
                  value={minQty}
                  onChange={(e) => setMinQty(Number(e.target.value))}
                />
              </div>
              <div className="flex justify-end space-x-2 pt-4">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">Create Plan</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

