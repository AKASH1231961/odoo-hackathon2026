import React, { useEffect, useState } from 'react'
import { invoicesApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function AdminInvoices() {
  const [invoices, setInvoices] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const loadInvoices = async () => {
    try {
      const res = await invoicesApi.list()
      setInvoices(res.data)
    } catch {
      toast.error('Failed to load invoices')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInvoices()
  }, [])

  const handleConfirm = async (id: string) => {
    try {
      await invoicesApi.confirm(id)
      toast.success('Invoice confirmed')
      loadInvoices()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to confirm')
    }
  }

  const handleSend = async (id: string) => {
    try {
      await invoicesApi.send(id)
      toast.success('Invoice sent via email')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to send')
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'paid': return <span className="badge-green">Paid</span>
      case 'confirmed': return <span className="badge-blue">Confirmed</span>
      case 'draft': return <span className="badge-yellow">Draft</span>
      case 'cancelled': return <span className="badge-red">Cancelled</span>
      default: return <span className="badge-gray">{status}</span>
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">Invoices</h2>
      </div>

      <div className="card overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>Number</th>
              <th>Due Date</th>
              <th>Subtotal</th>
              <th>Tax</th>
              <th>Discount</th>
              <th>Total</th>
              <th>Status</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="text-center py-4">Loading...</td></tr>
            ) : invoices.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-4">No invoices found</td></tr>
            ) : (
              invoices.map((inv) => (
                <tr key={inv.id}>
                  <td className="font-semibold text-gray-900">{inv.invoice_number}</td>
                  <td>{inv.due_date}</td>
                  <td>${Number(inv.subtotal).toFixed(2)}</td>
                  <td>${Number(inv.tax_total).toFixed(2)}</td>
                  <td>-${Number(inv.discount_total).toFixed(2)}</td>
                  <td className="font-bold text-gray-900">${Number(inv.grand_total).toFixed(2)}</td>
                  <td>{getStatusBadge(inv.status)}</td>
                  <td className="text-right space-x-2">
                    {inv.status === 'draft' && (
                      <button onClick={() => handleConfirm(inv.id)} className="btn-primary text-xs">Confirm</button>
                    )}
                    <button onClick={() => handleSend(inv.id)} className="btn-secondary text-xs">Send Email</button>
                    <a
                      href={invoicesApi.pdfUrl(inv.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-secondary text-xs inline-block"
                    >
                      PDF
                    </a>
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

