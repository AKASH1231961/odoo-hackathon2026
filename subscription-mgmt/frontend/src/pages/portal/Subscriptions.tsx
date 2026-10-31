import React, { useEffect, useState } from 'react'
import { portalApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function PortalSubscriptions() {
  const [subs, setSubs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const res = await portalApi.subscriptions()
        setSubs(res.data)
      } catch {
        toast.error('Failed to load subscriptions')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">My Subscriptions</h2>

      <div className="card overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>Subscription #</th>
              <th>Status</th>
              <th>Start Date</th>
              <th>Expiry Date</th>
              <th>Next Billing</th>
              <th>Terms</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-4">Loading...</td></tr>
            ) : subs.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-4">You have no subscriptions on file.</td></tr>
            ) : (
              subs.map((s) => (
                <tr key={s.id}>
                  <td className="font-semibold text-gray-900">{s.subscription_number}</td>
                  <td>
                    <span className={`badge ${s.status === 'active' ? 'badge-green' : 'badge-gray'}`}>
                      {s.status}
                    </span>
                  </td>
                  <td>{s.start_date || '—'}</td>
                  <td>{s.expiry_date || '—'}</td>
                  <td>{s.next_billing_date || '—'}</td>
                  <td>{s.payment_terms} days</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

