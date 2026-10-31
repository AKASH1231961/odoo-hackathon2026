import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  role: string | null
  email: string | null
  setTokens: (access: string, refresh: string) => void
  setRole: (role: string) => void
  setEmail: (email: string) => void
  logout: () => void
}

function parseJwt(token: string): Record<string, unknown> {
  try {
    return JSON.parse(atob(token.split('.')[1]))
  } catch {
    return {}
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      role: null,
      email: null,
      setTokens: (access, refresh) => {
        const payload = parseJwt(access)
        set({
          accessToken: access,
          refreshToken: refresh,
          role: payload.role as string,
        })
      },
      setRole: (role) => set({ role }),
      setEmail: (email) => set({ email }),
      logout: () =>
        set({ accessToken: null, refreshToken: null, role: null, email: null }),
    }),
    { name: 'brightloop-auth' }
  )
)

