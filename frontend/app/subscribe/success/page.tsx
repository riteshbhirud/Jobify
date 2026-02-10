'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Logo } from "@/components/shared/Logo"
import { CheckCircle } from "lucide-react"

export default function SubscribeSuccessPage() {
  const [countdown, setCountdown] = useState(5)
  const router = useRouter()

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          router.push('/onboarding')
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-primary/5 to-background py-12 px-4">
      <div className="w-full max-w-md text-center">
        <Logo className="inline-block mb-6" />

        <Card>
          <CardHeader>
            <div className="flex justify-center mb-4">
              <CheckCircle className="h-12 w-12 text-secondary" />
            </div>
            <CardTitle className="text-2xl">Welcome to ApplyAFK Pro!</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground">
              Your subscription is active. Let&apos;s set up your profile so we can start matching you with jobs.
            </p>

            <p className="text-sm text-muted-foreground">
              Redirecting to onboarding in {countdown} seconds...
            </p>

            <Button
              onClick={() => router.push('/onboarding')}
              className="w-full"
              size="lg"
            >
              Continue to Onboarding
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
