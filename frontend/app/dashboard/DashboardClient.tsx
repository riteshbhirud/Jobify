'use client'

import { useState } from "react"
import { createClient } from "@/lib/supabase/client"
import { StatusToggle } from "@/components/dashboard/StatusToggle"
import { StatsCards } from "@/components/dashboard/StatsCards"
import { RecentApplications } from "@/components/dashboard/RecentApplications"

interface DashboardClientProps {
  userId: string
  isActive: boolean
  stats: {
    today: number
    thisWeek: number
    total: number
    interviews: number
  }
  applications: any[]
}

export function DashboardClient({ userId, isActive: initialIsActive, stats, applications }: DashboardClientProps) {
  const [isActive, setIsActive] = useState(initialIsActive)
  const supabase = createClient()

  const handleToggle = async (active: boolean) => {
    const { error } = await supabase
      .from('users')
      .update({ is_active: active })
      .eq('id', userId)

    if (error) {
      console.error('Error updating automation status:', error)
      throw error
    }

    setIsActive(active)
  }

  return (
    <div className="space-y-8">
      <StatusToggle isActive={isActive} onToggle={handleToggle} />
      <StatsCards stats={stats} />
      <RecentApplications applications={applications} />
    </div>
  )
}
