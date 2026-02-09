'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Logo } from "@/components/shared/Logo"
import { LoadingSpinner } from "@/components/shared/LoadingSpinner"
import { Check } from "lucide-react"

export default function SubscribePage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const supabase = createClient()

  const handleSubscribe = async () => {
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

      // Redirect to Stripe Checkout — card data never touches our servers
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
          <h1 className="text-2xl font-bold mb-2">Start Your Free Trial</h1>
          <p className="text-muted-foreground">
            7 days free, then $2/month. Cancel anytime.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>ApplyAFK Pro</CardTitle>
            <CardDescription>Automate your job applications</CardDescription>
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
              <p className="text-sm text-muted-foreground">after 7-day free trial</p>
            </div>

            {error && (
              <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-md text-sm">
                {error}
              </div>
            )}

            <Button
              onClick={handleSubscribe}
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
                'Start Free Trial'
              )}
            </Button>

            <p className="text-xs text-center text-muted-foreground">
              You will be redirected to Stripe for secure payment.
              Your card will not be charged during the trial period.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
