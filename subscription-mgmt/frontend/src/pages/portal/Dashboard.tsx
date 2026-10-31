import React, { useEffect, useState } from 'react'
import { portalApi } from '../../api/client'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'

export default function PortalDashboard() {
  const [subs, setSubs] = useState<any[]>([])
  const [invoices, setInvoices] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const [subsRes, invsRes] = await Promise.all([
          portalApi.subscriptions(),
          portalApi.invoices(),
        ])
        setSubs(subsRes.data)
        setInvoices(invsRes.data)
      } catch {
        toast.error('Failed to load portal data')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  if (loading) return <div className="text-gray-500">Loading your account...</div>

  const activeSubs = subs.filter((s) => s.status === 'active')
  const unpaidInvoices = invoices.filter((i) => i.status !== 'paid')

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <p className="text-sm font-medium text-gray-500">Active Subscriptions</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{activeSubs.length}</p>
        </div>
        <div className="card">
          <p className="text-sm font-medium text-gray-500">Unpaid Invoices</p>
          <p className="text-3xl font-bold text-yellow-600 mt-2">{unpaidInvoices.length}</p>
        </div>
        <div className="card">
          <p className="text-sm font-medium text-gray-500">Total Billed</p>
          <p className="text-3xl font-bold text-brand-900 mt-2">
            ${invoices.reduce((acc, curr) => acc + Number(curr.grand_total), 0).toFixed(2)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-gray-900">Your Subscriptions</h3>
            <Link to="/portal/subscriptions" className="text-sm text-brand-700 hover:underline">View all</Link>
          </div>
          {subs.length === 0 ? (
            <p className="text-sm text-gray-500">No subscriptions found.</p>
          ) : (
            <div className="space-y-3">
              {subs.slice(0, 3).map((s) => (
                <div key={s.id} className="flex justify-between items-center border-b pb-2">
                  <div>
                    <p className="font-semibold text-sm">{s.subscription_number}</p>
                    <p className="text-xs text-gray-500">Next billing: {s.next_billing_date || '—'}</p>
                  </div>
                  <span className={`badge ${s.status === 'active' ? 'badge-green' : 'badge-gray'}`}>
                    {s.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-gray-900">Recent Invoices</h3>
            <Link to="/portal/invoices" className="text-sm text-brand-700 hover:underline">View all</Link>
          </div>
          {invoices.length === 0 ? (
            <p className="text-sm text-gray-500">No invoices yet.</p>
          ) : (
            <div className="space-y-3">
              {invoices.slice(0, 3).map((i) => (
                <div key={i.id} className="flex justify-between items-center border-b pb-2">
                  <div>
                    <p className="font-semibold text-sm">{i.invoice_number}</p>
                    <p className="text-xs text-gray-500">Due: {i.due_date}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-sm">${Number(i.grand_total).toFixed(2)}</p>
                    <span className={`badge text-[10px] ${i.status === 'paid' ? 'badge-green' : 'badge-yellow'}`}>
                      {i.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

