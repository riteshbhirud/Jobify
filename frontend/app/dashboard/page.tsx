// frontend/app/dashboard/page.tsx

import { redirect } from 'next/navigation'
import { createServerSupabaseClient } from '@/lib/supabase/server'
import { DashboardClient } from './DashboardClient'

export default async function DashboardPage() {
  const supabase = await createServerSupabaseClient()

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  const { data: profile } = await supabase
    .from('users')
    .select('*')
    .eq('id', user.id)
    .single()

  if (!profile) {
    redirect('/onboarding')
  }

  // Get applications (mock data for now - you'll create the applications table)
  const applications: any[] = []

  // Calculate stats (will be real once you have applications table)
  const stats = {
    today: 0,
    thisWeek: 0,
    total: 0,
    interviews: 0,
  }

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">
          Welcome back, {profile.first_name || 'there'}! 👋
        </h1>
        <p className="text-muted-foreground">
          Track your automated job applications and manage your settings
        </p>
      </div>

      <DashboardClient
        userId={user.id}
        isActive={profile.is_active || false}
        stats={stats}
        applications={applications}
      />
    </div>
  )
}
