import axios from 'axios'
import { useAuthStore } from '../store/auth'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// Auto-attach Bearer token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-refresh on 401
let isRefreshing = false
let failedQueue: Array<{ resolve: (v: string) => void; reject: (e: unknown) => void }> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token!)
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = useAuthStore.getState().refreshToken
      try {
        const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
          refresh_token: refreshToken,
        })
        const newToken = data.access_token
        useAuthStore.getState().setTokens(newToken, data.refresh_token)
        processQueue(null, newToken)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return api(originalRequest)
      } catch (err) {
        processQueue(err)
        useAuthStore.getState().logout()
        window.location.href = '/login'
        return Promise.reject(err)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

// ── API helpers ──────────────────────────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (email: string, password: string, fullName?: string) =>
    api.post('/auth/register', { email, password, full_name: fullName }),
  forgotPassword: (email: string) =>
    api.post('/auth/forgot-password', { email }),
  resetPassword: (token: string, newPassword: string) =>
    api.post('/auth/reset-password', { token, new_password: newPassword }),
}

export const productsApi = {
  list: (params?: object) => api.get('/products', { params }),
  get: (id: string) => api.get(`/products/${id}`),
  create: (data: object) => api.post('/products', data),
  update: (id: string, data: object) => api.patch(`/products/${id}`, data),
  deactivate: (id: string) => api.delete(`/products/${id}`),
  addVariant: (productId: string, data: object) =>
    api.post(`/products/${productId}/variants`, data),
}

export const plansApi = {
  list: (params?: object) => api.get('/plans', { params }),
  get: (id: string) => api.get(`/plans/${id}`),
  create: (data: object) => api.post('/plans', data),
  update: (id: string, data: object) => api.patch(`/plans/${id}`, data),
  close: (id: string) => api.post(`/plans/${id}/close`),
}

export const subscriptionsApi = {
  list: (params?: object) => api.get('/subscriptions', { params }),
  get: (id: string) => api.get(`/subscriptions/${id}`),
  create: (data: object) => api.post('/subscriptions', data),
  confirm: (id: string) => api.post(`/subscriptions/${id}/confirm`),
  activate: (id: string) => api.post(`/subscriptions/${id}/activate`),
  pause: (id: string) => api.post(`/subscriptions/${id}/pause`),
  resume: (id: string) => api.post(`/subscriptions/${id}/resume`),
  close: (id: string) => api.post(`/subscriptions/${id}/close`),
  renew: (id: string) => api.post(`/subscriptions/${id}/renew`),
}

export const invoicesApi = {
  list: (params?: object) => api.get('/invoices', { params }),
  get: (id: string) => api.get(`/invoices/${id}`),
  confirm: (id: string) => api.post(`/invoices/${id}/confirm`),
  cancel: (id: string) => api.post(`/invoices/${id}/cancel`),
  send: (id: string) => api.post(`/invoices/${id}/send`),
  pdfUrl: (id: string) => `${API_BASE}/invoices/${id}/pdf`,
  generate: (subscriptionId: string) =>
    api.post(`/invoices/generate/${subscriptionId}`),
}

export const paymentsApi = {
  list: (params?: object) => api.get('/payments', { params }),
  record: (data: object) => api.post('/payments', data),
  update: (id: string, data: object) => api.patch(`/payments/${id}`, data),
}

export const taxRulesApi = {
  list: () => api.get('/tax-rules'),
  create: (data: object) => api.post('/tax-rules', data),
  update: (id: string, data: object) => api.patch(`/tax-rules/${id}`, data),
  deactivate: (id: string) => api.delete(`/tax-rules/${id}`),
}

export const discountsApi = {
  list: () => api.get('/discounts'),
  create: (data: object) => api.post('/discounts', data),
  update: (id: string, data: object) => api.patch(`/discounts/${id}`, data),
  deactivate: (id: string) => api.delete(`/discounts/${id}`),
}

export const usersApi = {
  list: (params?: object) => api.get('/users', { params }),
  me: () => api.get('/users/me'),
  createStaff: (data: object) => api.post('/users', data),
  deactivate: (id: string) => api.patch(`/users/${id}/deactivate`),
}

export const reportsApi = {
  summary: () => api.get('/reports/summary'),
  revenue: (from: string, to: string) =>
    api.get('/reports/revenue', { params: { from, to } }),
  overdue: () => api.get('/reports/overdue'),
}

export const portalApi = {
  subscriptions: () => api.get('/portal/subscriptions'),
  subscription: (id: string) => api.get(`/portal/subscriptions/${id}`),
  invoices: () => api.get('/portal/invoices'),
  invoice: (id: string) => api.get(`/portal/invoices/${id}`),
  invoicePdfUrl: (id: string) => `${API_BASE}/portal/invoices/${id}/pdf`,
  profile: () => api.get('/portal/profile'),
  updateProfile: (data: object) => api.patch('/portal/profile', data),
}

