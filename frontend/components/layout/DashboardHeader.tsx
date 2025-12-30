'use client'

import { useState } from "react"
import { useRouter } from "next/navigation"
import { createClient } from "@/lib/supabase/client"
import { Button } from "@/components/ui/button"

interface DashboardHeaderProps {
  user: {
    email?: string | undefined
    id: string
  }
}

export function DashboardHeader({ user }: DashboardHeaderProps) {
  const [loading, setLoading] = useState(false)
  const router = useRouter()
  const supabase = createClient()

  const handleSignOut = async () => {
    setLoading(true)
    await supabase.auth.signOut()
    router.push('/auth/login')
  }

  return (
    <div className="bg-background border-b">
      <div className="flex justify-between items-center h-16 px-6">
        <div className="flex items-center md:hidden">
          <span className="text-xl font-bold">Jobify</span>
        </div>

        <div className="flex-1" />

        <div className="flex items-center space-x-4">
          <div className="hidden sm:block text-sm text-muted-foreground">
            {user.email}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSignOut}
            disabled={loading}
          >
            {loading ? 'Signing out...' : 'Sign Out'}
          </Button>
        </div>
      </div>
    </div>
  )
}
