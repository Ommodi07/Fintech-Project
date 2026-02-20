"use client"

import { SignupForm } from "@/components/signup-form"
import { authClient } from "@/lib/authApi"
import { GalleryVerticalEndIcon } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

export default function SignupPage() {
  const router = useRouter()
  const { data: session, isPending } = authClient.useSession()

  useEffect(() => {
    if (isPending) return
    if (session) router.replace("/")
  }, [session, isPending, router])

  if (isPending) {
    return (
      <div className="bg-muted flex min-h-svh items-center justify-center">
        <div className="size-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  if (session) return null

  return (
    <div className="bg-muted flex min-h-svh flex-col items-center justify-center gap-6 p-6 md:p-10">
      <div className="flex w-full max-w-sm flex-col gap-6">
        <a href="/" className="flex items-center gap-2 self-center font-medium">
          <div className="bg-primary text-primary-foreground flex size-6 items-center justify-center rounded-md">
            <GalleryVerticalEndIcon className="size-4" />
          </div>
          Acme Inc.
        </a>
        <SignupForm />
      </div>
    </div>
  )
}
