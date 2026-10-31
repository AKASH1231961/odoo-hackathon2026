import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/auth'

interface Props {
  allowedRoles: string[]
}

export default function ProtectedRoute({ allowedRoles }: Props) {
  const { accessToken, role } = useAuthStore()

  if (!accessToken) return <Navigate to="/login" replace />
  if (!allowedRoles.includes(role ?? '')) return <Navigate to="/" replace />

  return <Outlet />
}

