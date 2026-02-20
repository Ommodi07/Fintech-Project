"use client"

import { authClient } from "@/lib/authApi"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { data: session, isPending } = authClient.useSession()

  useEffect(() => {
    if (isPending) return
    if (!session) {
      router.replace("/login")
    }
  }, [session, isPending, router])

  if (isPending) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-muted">
        <div className="flex flex-col items-center gap-4">
          <div className="size-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Checking authentication...</p>
        </div>
      </div>
    )
  }

  if (!session) {
    return null
  }

  return <>{children}</>
}
