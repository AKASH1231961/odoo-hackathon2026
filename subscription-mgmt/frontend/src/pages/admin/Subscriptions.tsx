import React, { useEffect, useState } from 'react'
import { subscriptionsApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function AdminSubscriptions() {
  const [subs, setSubs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const loadSubscriptions = async () => {
    try {
      const res = await subscriptionsApi.list()
      setSubs(res.data)
    } catch {
      toast.error('Failed to load subscriptions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSubscriptions()
  }, [])

  const handleAction = async (id: string, action: string) => {
    try {
      if (action === 'confirm') await subscriptionsApi.confirm(id)
      if (action === 'activate') await subscriptionsApi.activate(id)
      if (action === 'pause') await subscriptionsApi.pause(id)
      if (action === 'resume') await subscriptionsApi.resume(id)
      if (action === 'close') await subscriptionsApi.close(id)
      if (action === 'renew') await subscriptionsApi.renew(id)
      toast.success(`Action '${action}' executed successfully`)
      loadSubscriptions()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || `Failed to execute ${action}`)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active': return <span className="badge-green">Active</span>
      case 'confirmed': return <span className="badge-blue">Confirmed</span>
      case 'paused': return <span className="badge-yellow">Paused</span>
      case 'closed': return <span className="badge-gray">Closed</span>
      default: return <span className="badge-gray">{status}</span>
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">Manage Subscriptions</h2>
      </div>

      <div className="card overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>Number</th>
              <th>Customer</th>
              <th>Status</th>
              <th>Next Billing</th>
              <th>Start Date</th>
              <th>Terms</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="text-center py-4">Loading...</td></tr>
            ) : subs.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-4">No subscriptions found</td></tr>
            ) : (
              subs.map((sub) => (
                <tr key={sub.id}>
                  <td className="font-semibold text-gray-900">{sub.subscription_number}</td>
                  <td className="text-gray-600">{sub.customer_id.slice(0, 8)}...</td>
                  <td>{getStatusBadge(sub.status)}</td>
                  <td>{sub.next_billing_date || '—'}</td>
                  <td>{sub.start_date || '—'}</td>
                  <td>{sub.payment_terms} days</td>
                  <td className="text-right space-x-2">
                    {sub.status === 'draft' && (
                      <button onClick={() => handleAction(sub.id, 'confirm')} className="btn-secondary text-xs">Confirm</button>
                    )}
                    {sub.status === 'confirmed' && (
                      <button onClick={() => handleAction(sub.id, 'activate')} className="btn-primary text-xs">Activate</button>
                    )}
                    {sub.status === 'active' && (
                      <>
                        <button onClick={() => handleAction(sub.id, 'pause')} className="btn-secondary text-xs">Pause</button>
                        <button onClick={() => handleAction(sub.id, 'close')} className="btn-danger text-xs">Close</button>
                      </>
                    )}
                    {sub.status === 'paused' && (
                      <button onClick={() => handleAction(sub.id, 'resume')} className="btn-primary text-xs">Resume</button>
                    )}
                    {sub.status === 'closed' && (
                      <button onClick={() => handleAction(sub.id, 'renew')} className="btn-secondary text-xs">Renew</button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

