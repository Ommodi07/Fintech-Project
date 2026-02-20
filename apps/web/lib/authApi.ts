import { createAuthClientInstance } from "@repo/auth/src/client"

const AUTH_BASE_URL =
  process.env.NEXT_PUBLIC_AUTH_URL || "http://localhost:3001"

export const authClient = createAuthClientInstance({ baseURL: AUTH_BASE_URL })
