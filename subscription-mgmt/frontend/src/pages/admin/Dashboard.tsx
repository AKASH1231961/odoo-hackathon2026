import React, { useEffect, useState } from 'react'
import { reportsApi } from '../../api/client'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import toast from 'react-hot-toast'

export default function AdminDashboard() {
  const [summary, setSummary] = useState<any>(null)
  const [revenueData, setRevenueData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const [sumRes, revRes] = await Promise.all([
          reportsApi.summary(),
          reportsApi.revenue('2026-01-01', '2026-12-31'),
        ])
        setSummary(sumRes.data)
        setRevenueData(revRes.data)
      } catch (err: any) {
        toast.error('Failed to load dashboard metrics')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  if (loading) return <div className="text-gray-500">Loading metrics...</div>

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card">
          <p className="text-sm font-medium text-gray-500">Active Subscriptions</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{summary?.active_subscription_count ?? 0}</p>
        </div>
        <div className="card">
          <p className="text-sm font-medium text-gray-500">Revenue (This Month)</p>
          <p className="text-3xl font-bold text-green-600 mt-2">
            ${summary?.total_revenue_this_month?.toLocaleString() ?? 0}
          </p>
        </div>
        <div className="card">
          <p className="text-sm font-medium text-gray-500">Outstanding Invoices</p>
          <p className="text-3xl font-bold text-yellow-600 mt-2">
            ${summary?.outstanding_amount?.toLocaleString() ?? 0}
          </p>
        </div>
        <div className="card">
          <p className="text-sm font-medium text-gray-500">Overdue Invoices</p>
          <p className="text-3xl font-bold text-red-600 mt-2">{summary?.overdue_invoice_count ?? 0}</p>
        </div>
      </div>

      {/* Revenue Chart */}
      <div className="card">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Monthly Revenue Overview</h3>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={revenueData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip formatter={(value: any) => [`$${value}`, 'Revenue']} />
              <Bar dataKey="revenue" fill="#1e3a8a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

