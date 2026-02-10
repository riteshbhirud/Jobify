// frontend/app/dashboard/page.tsx

import { redirect } from 'next/navigation'
import { createServerSupabaseClient } from '@/lib/supabase/server'
import { DashboardClient } from './DashboardClient'

export const dynamic = 'force-dynamic'

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

  // Fetch recent applications with joined job data
  const { data: applications } = await supabase
    .from('applications')
    .select('id, status, match_score, submitted_at, created_at, jobs(title, company)')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })
    .limit(10)

  // Map to the shape the RecentApplications component expects
  const recentApps = (applications || []).map((app: any) => ({
    id: app.id,
    job_title: app.jobs?.title || 'Unknown Position',
    company_name: app.jobs?.company || 'Unknown Company',
    status: app.status,
    applied_at: app.submitted_at || app.created_at,
  }))

  // Calculate real stats
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString()
  const weekStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - now.getDay()).toISOString()

  const { count: todayCount } = await supabase
    .from('applications')
    .select('id', { count: 'exact', head: true })
    .eq('user_id', user.id)
    .eq('status', 'submitted')
    .gte('submitted_at', todayStart)

  const { count: weekCount } = await supabase
    .from('applications')
    .select('id', { count: 'exact', head: true })
    .eq('user_id', user.id)
    .eq('status', 'submitted')
    .gte('submitted_at', weekStart)

  const { count: totalCount } = await supabase
    .from('applications')
    .select('id', { count: 'exact', head: true })
    .eq('user_id', user.id)
    .eq('status', 'submitted')

  const stats = {
    today: todayCount || 0,
    thisWeek: weekCount || 0,
    total: totalCount || 0,
    interviews: 0,
  }

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">
          Welcome back, {profile.first_name || 'there'}!
        </h1>
        <p className="text-muted-foreground">
          Track your automated job applications and manage your settings
        </p>
      </div>

      <DashboardClient
        userId={user.id}
        isActive={profile.is_active || false}
        stats={stats}
        applications={recentApps}
      />
    </div>
  )
}
