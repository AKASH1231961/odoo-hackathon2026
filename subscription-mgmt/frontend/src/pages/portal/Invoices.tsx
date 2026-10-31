import React, { useEffect, useState } from 'react'
import { portalApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function PortalInvoices() {
  const [invoices, setInvoices] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const res = await portalApi.invoices()
        setInvoices(res.data)
      } catch {
        toast.error('Failed to load invoices')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-900">My Invoices</h2>

      <div className="card overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Due Date</th>
              <th>Subtotal</th>
              <th>Tax</th>
              <th>Discount</th>
              <th>Total</th>
              <th>Status</th>
              <th className="text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="text-center py-4">Loading...</td></tr>
            ) : invoices.length === 0 ? (
              <tr><td colSpan={8} className="text-center py-4">No invoices on file.</td></tr>
            ) : (
              invoices.map((inv) => (
                <tr key={inv.id}>
                  <td className="font-semibold text-gray-900">{inv.invoice_number}</td>
                  <td>{inv.due_date}</td>
                  <td>${Number(inv.subtotal).toFixed(2)}</td>
                  <td>${Number(inv.tax_total).toFixed(2)}</td>
                  <td>-${Number(inv.discount_total).toFixed(2)}</td>
                  <td className="font-bold text-gray-900">${Number(inv.grand_total).toFixed(2)}</td>
                  <td>
                    <span className={`badge ${inv.status === 'paid' ? 'badge-green' : 'badge-yellow'}`}>
                      {inv.status}
                    </span>
                  </td>
                  <td className="text-right">
                    <a
                      href={portalApi.invoicePdfUrl(inv.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-secondary text-xs inline-block"
                    >
                      Download PDF
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

