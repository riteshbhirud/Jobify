'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { Button } from "@/components/ui/button"
import { LoadingSpinner } from "@/components/shared/LoadingSpinner"

export function BillingButton() {
  const [loading, setLoading] = useState(false)
  const supabase = createClient()

  const handleManageBilling = async () => {
    setLoading(true)

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) return

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL!}/api/payments/create-portal-session`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
        }
      )

      const data = await response.json()

      if (response.ok && data.portal_url) {
        window.location.href = data.portal_url
      }
    } catch {
      // Silently fail — user can retry
    } finally {
      setLoading(false)
    }
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleManageBilling}
      disabled={loading}
    >
      {loading ? (
        <span className="flex items-center">
          <LoadingSpinner size="sm" className="mr-2" />
          Loading...
        </span>
      ) : (
        'Manage Billing'
      )}
    </Button>
  )
}
