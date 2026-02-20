"use client"

import { cn } from "@repo/ui/lib/utils"
import { Button } from "@repo/ui/components/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@repo/ui/components/card"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@repo/ui/components/field"
import { Input } from "@repo/ui/components/input"
import { useForm } from "@tanstack/react-form"
import { useResetPassword } from "@/lib/hooks/useAuth"
import Link from "next/link"
import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"

export function ResetPasswordForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  const searchParams = useSearchParams()
  const resetMutation = useResetPassword()
  const [error, setError] = useState<string | null>(null)
  const [token, setToken] = useState<string | null>(null)

  useEffect(() => {
    const tokenParam = searchParams.get("token")
    const errorParam = searchParams.get("error")

    if (errorParam === "INVALID_TOKEN") {
      setError("Invalid or expired reset token. Please request a new password reset.")
    } else if (tokenParam) {
      setToken(tokenParam)
    } else {
      setError("No reset token provided. Please check your email for the reset link.")
    }
  }, [searchParams])

  const form = useForm({
    defaultValues: {
      newPassword: "",
      confirmPassword: "",
    },
    onSubmit: async ({ value }) => {
      if (!token) {
        setError("No reset token available")
        return
      }

      setError(null)
      try {
        await resetMutation.mutateAsync({
          newPassword: value.newPassword,
          token,
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to reset password")
      }
    },
  })

  if (!token && !error) {
    return (
      <div className={cn("flex flex-col gap-6", className)} {...props}>
        <Card>
          <CardContent>
            <div className="p-4 text-center">Loading...</div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Reset your password</CardTitle>
          <CardDescription>
            Enter your new password below
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              e.stopPropagation()
              form.handleSubmit()
            }}
          >
            <FieldGroup>
              {error && (
                <Field>
                  <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
                    {error}
                  </div>
                </Field>
              )}
              {token && (
                <>
                  <form.Field
                    name="newPassword"
                    validators={{
                      onChange: ({ value }) => {
                        if (!value) return "Password is required"
                        if (value.length < 8) {
                          return "Password must be at least 8 characters long"
                        }
                        return undefined
                      },
                    }}
                  >
                    {(field) => (
                      <Field>
                        <FieldLabel htmlFor={field.name}>New Password</FieldLabel>
                        <Input
                          id={field.name}
                          type="password"
                          value={field.state.value}
                          onChange={(e) => field.handleChange(e.target.value)}
                          onBlur={field.handleBlur}
                          required
                        />
                        {field.state.meta.errors && (
                          <FieldDescription className="text-destructive">
                            {field.state.meta.errors[0]}
                          </FieldDescription>
                        )}
                      </Field>
                    )}
                  </form.Field>
                  <form.Field
                    name="confirmPassword"
                    validators={{
                      onChange: ({ value }) => {
                        if (!value) return "Please confirm your password"
                        const password = form.getFieldValue("newPassword")
                        if (value !== password) {
                          return "Passwords do not match"
                        }
                        return undefined
                      },
                    }}
                  >
                    {(field) => (
                      <Field>
                        <FieldLabel htmlFor={field.name}>Confirm Password</FieldLabel>
                        <Input
                          id={field.name}
                          type="password"
                          value={field.state.value}
                          onChange={(e) => field.handleChange(e.target.value)}
                          onBlur={field.handleBlur}
                          required
                        />
                        {field.state.meta.errors && (
                          <FieldDescription className="text-destructive">
                            {field.state.meta.errors[0]}
                          </FieldDescription>
                        )}
                      </Field>
                    )}
                  </form.Field>
                  <Field>
                    <FieldDescription>
                      Password must be at least 8 characters long.
                    </FieldDescription>
                  </Field>
                  <Field>
                    <Button
                      type="submit"
                      disabled={resetMutation.isPending || !token}
                      className="w-full"
                    >
                      {resetMutation.isPending ? "Resetting..." : "Reset password"}
                    </Button>
                    <FieldDescription className="text-center">
                      Remember your password?{" "}
                      <Link href="/login" className="underline-offset-4 hover:underline">
                        Sign in
                      </Link>
                    </FieldDescription>
                  </Field>
                </>
              )}
              {!token && error && (
                <Field>
                  <Button asChild className="w-full">
                    <Link href="/forgot-password">Request new reset link</Link>
                  </Button>
                </Field>
              )}
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
