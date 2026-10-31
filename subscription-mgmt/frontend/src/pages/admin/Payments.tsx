import React, { useEffect, useState } from 'react'
import { paymentsApi } from '../../api/client'
import toast from 'react-hot-toast'

export default function AdminPayments() {
  const [payments, setPayments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  // Record payment form modal
  const [showModal, setShowModal] = useState(false)
  const [invoiceId, setInvoiceId] = useState('')
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState('bank_transfer')
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().split('T')[0])
  const [reference, setReference] = useState('')
  const [note, setNote] = useState('')

  const loadPayments = async () => {
    try {
      const res = await paymentsApi.list()
      setPayments(res.data)
    } catch {
      toast.error('Failed to load payments')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPayments()
  }, [])

  const handleRecord = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await paymentsApi.record({
        invoice_id: invoiceId,
        amount: Number(amount),
        method,
        payment_date: paymentDate,
        reference,
        note,
      })
      toast.success('Payment recorded successfully')
      setShowModal(false)
      loadPayments()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to record payment')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">Payments</h2>
        <button onClick={() => setShowModal(true)} className="btn-primary">Record Payment</button>
      </div>

      <div className="card overflow-x-auto">
        <table>
          <thead>
            <tr>
              <th>Invoice ID</th>
              <th>Amount</th>
              <th>Method</th>
              <th>Date</th>
              <th>Reference</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-4">Loading...</td></tr>
            ) : payments.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-4">No payments recorded</td></tr>
            ) : (
              payments.map((p) => (
                <tr key={p.id}>
                  <td className="font-semibold text-gray-900">{p.invoice_id.slice(0, 8)}...</td>
                  <td className="font-bold text-green-700">${Number(p.amount).toFixed(2)}</td>
                  <td className="uppercase text-xs font-semibold">{p.method}</td>
                  <td>{p.payment_date}</td>
                  <td>{p.reference || '—'}</td>
                  <td>{p.note || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold">Record Payment</h3>
            <form onSubmit={handleRecord} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-gray-600">Invoice ID</label>
                <input
                  type="text"
                  required
                  className="input mt-1"
                  placeholder="UUID"
                  value={invoiceId}
                  onChange={(e) => setInvoiceId(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Amount ($)</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  className="input mt-1"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Payment Method</label>
                <select className="input mt-1" value={method} onChange={(e) => setMethod(e.target.value)}>
                  <option value="bank_transfer">Bank Transfer</option>
                  <option value="card">Credit/Debit Card</option>
                  <option value="upi">UPI</option>
                  <option value="cash">Cash</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Payment Date</label>
                <input
                  type="date"
                  required
                  className="input mt-1"
                  value={paymentDate}
                  onChange={(e) => setPaymentDate(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-600">Reference / Transaction ID</label>
                <input
                  type="text"
                  className="input mt-1"
                  placeholder="e.g. TXN-998822"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                />
              </div>
              <div className="flex justify-end space-x-2 pt-4">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">Save Payment</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

