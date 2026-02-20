import { useMutation } from "@tanstack/react-query"
import { authClient } from "@/lib/authApi"
import { useRouter } from "next/navigation"

export function useLogin() {
  const router = useRouter()

  return useMutation({
    mutationFn: async (data: { email: string; password: string; rememberMe?: boolean }) => {
      const result = await authClient.signIn.email({
        email: data.email,
        password: data.password,
        rememberMe: data.rememberMe ?? true,
      })

      if (result.error) {
        throw new Error(result.error.message || "Login failed")
      }

      return result.data
    },
    onSuccess: () => {
      router.push("/")
      router.refresh()
    },
  })
}

export function useSignup() {
  const router = useRouter()

  return useMutation({
    mutationFn: async (data: {
      name: string
      email: string
      password: string
      image?: string
    }) => {
      const result = await authClient.signUp.email({
        name: data.name,
        email: data.email,
        password: data.password,
        image: data.image,
      })

      if (result.error) {
        throw new Error(result.error.message || "Signup failed")
      }

      return result.data
    },
    onSuccess: () => {
      router.push("/login")
    },
  })
}

export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: async (data: { email: string; redirectTo?: string }) => {
      const result = await authClient.requestPasswordReset({
        email: data.email,
        redirectTo: data.redirectTo,
      })

      if (result.error) {
        throw new Error(result.error.message || "Failed to request password reset")
      }

      return result.data
    },
  })
}

export function useResetPassword() {
  const router = useRouter()

  return useMutation({
    mutationFn: async (data: { newPassword: string; token: string }) => {
      const result = await authClient.resetPassword({
        newPassword: data.newPassword,
        token: data.token,
      })

      if (result.error) {
        throw new Error(result.error.message || "Failed to reset password")
      }

      return result.data
    },
    onSuccess: () => {
      router.push("/login")
    },
  })
}

export function useSignOut() {
  const router = useRouter()

  return useMutation({
    mutationFn: async () => {
      const result = await authClient.signOut({})

      if (result.error) {
        throw new Error(result.error.message || "Sign out failed")
      }

      return result.data
    },
    onSuccess: () => {
      router.push("/login")
      router.refresh()
    },
  })
}
