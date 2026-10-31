import React, { useEffect, useState } from 'react'
import { reportsApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function AdminReports() {
  const [overdue, setOverdue] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const res = await reportsApi.overdue()
        setOverdue(res.data)
      } catch {
        toast.error('Failed to load overdue report')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">Overdue Invoices & Collection Chasing</h2>
      </div>

      <div className="card overflow-x-auto">
        <div className="mb-4">
          <p className="text-sm text-gray-600">
            Invoices currently confirmed and past their due date, sorted by urgency.
          </p>
        </div>
        <table>
          <thead>
            <tr>
              <th>Invoice Number</th>
              <th>Customer</th>
              <th>Due Date</th>
              <th>Days Overdue</th>
              <th>Grand Total</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="text-center py-4">Loading report...</td></tr>
            ) : overdue.length === 0 ? (
              <tr><td colSpan={5} className="text-center py-4 text-green-600 font-medium">No overdue invoices found.</td></tr>
            ) : (
              overdue.map((item) => (
                <tr key={item.invoice_id}>
                  <td className="font-semibold text-gray-900">{item.invoice_number}</td>
                  <td className="text-gray-600">{item.customer_id.slice(0, 8)}...</td>
                  <td>{item.due_date}</td>
                  <td>
                    <span className="badge-red font-semibold">{item.days_overdue} days</span>
                  </td>
                  <td className="font-bold text-red-700">${item.grand_total.toFixed(2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

