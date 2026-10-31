import React, { useEffect, useState } from 'react'
import { productsApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function AdminProducts() {
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const [showModal, setShowModal] = useState(false)
  const [name, setName] = useState('')
  const [type, setType] = useState('Software')
  const [salesPrice, setSalesPrice] = useState('')
  const [costPrice, setCostPrice] = useState('')
  const [notes, setNotes] = useState('')

  const loadProducts = async () => {
    try {
      const res = await productsApi.list()
      setProducts(res.data)
    } catch {
      toast.error('Failed to load products')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProducts()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await productsApi.create({
        name,
        type,
        sales_price: Number(salesPrice),
        cost_price: costPrice ? Number(costPrice) : undefined,
        notes,
      })
      toast.success('Product created')
      setShowModal(false)
      setName('')
      setSalesPrice('')
      loadProducts()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create product')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">Products & Offerings</h2>
        <button onClick={() => setShowModal(true)} className="btn-primary">Add Product</button>
      </div>

      <div className="card overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Sales Price</th>
              <th>Cost Price</th>
              <th>Variants</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-4">Loading...</td></tr>
            ) : products.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-4">No products found</td></tr>
            ) : (
              products.map((p) => (
                <tr key={p.id}>
                  <td className="font-semibold text-gray-900">{p.name}</td>
                  <td>{p.type || '—'}</td>
                  <td className="font-semibold text-gray-900">${Number(p.sales_price).toFixed(2)}</td>
                  <td>{p.cost_price ? `$${Number(p.cost_price).toFixed(2)}` : '—'}</td>
                  <td>{p.variants?.length ? `${p.variants.length} variant(s)` : 'None'}</td>
                  <td>
                    {p.is_active ? <span className="badge-green">Active</span> : <span className="badge-gray">Inactive</span>}
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
            <h3 className="text-lg font-bold">New Product</h3>
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-gray-600">Product Name</label>
                <input
                  type="text"
                  required
                  className="input mt-1"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Type</label>
                <input
                  type="text"
                  className="input mt-1"
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-600">Sales Price ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    className="input mt-1"
                    value={salesPrice}
                    onChange={(e) => setSalesPrice(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-600">Cost Price ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    className="input mt-1"
                    value={costPrice}
                    onChange={(e) => setCostPrice(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Notes</label>
                <textarea
                  className="input mt-1"
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
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

