'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Logo } from "@/components/shared/Logo"
import { LoadingSpinner } from "@/components/shared/LoadingSpinner"
import { Check } from "lucide-react"

export default function ReactivatePage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const supabase = createClient()

  const handleResubscribe = async () => {
    setLoading(true)
    setError(null)

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        router.push('/auth/login')
        return
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL!}/api/payments/create-checkout-session`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to create checkout session')
      }

      window.location.href = data.checkout_url
    } catch (err: any) {
      setError(err.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  const features = [
    "Unlimited automated applications",
    "AI-powered job matching",
    "Cover letter generation",
    "Multi-platform ATS support",
  ]

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-primary/5 to-background py-12 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Logo className="inline-block mb-6" />
          <h1 className="text-2xl font-bold mb-2">Your Subscription Has Ended</h1>
          <p className="text-muted-foreground">
            Resubscribe to continue using ApplyAFK. Your profile and data are still saved.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>ApplyAFK Pro</CardTitle>
            <CardDescription>Pick up where you left off</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-3 text-sm">
              {features.map((feature) => (
                <li key={feature} className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-secondary flex-shrink-0" />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>

            <div className="pt-4 border-t">
              <p className="text-3xl font-bold">
                $2<span className="text-sm font-normal text-muted-foreground">/month</span>
              </p>
            </div>

            {error && (
              <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-md text-sm">
                {error}
              </div>
            )}

            <Button
              onClick={handleResubscribe}
              disabled={loading}
              className="w-full"
              size="lg"
            >
              {loading ? (
                <span className="flex items-center">
                  <LoadingSpinner size="sm" className="mr-2" />
                  Redirecting to checkout...
                </span>
              ) : (
                'Resubscribe — $2/month'
              )}
            </Button>

            <p className="text-xs text-center text-muted-foreground">
              You will be redirected to Stripe for secure payment.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
