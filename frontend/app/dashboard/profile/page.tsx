import { redirect } from 'next/navigation'
import { createServerSupabaseClient } from '@/lib/supabase/server'
import { ProfileClient } from '@/components/profile/ProfileClient'

export const dynamic = 'force-dynamic'

export default async function ProfilePage() {
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

  return (
    <div className="container mx-auto px-6 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Profile</h1>
        <p className="text-muted-foreground">
          View and update your profile information
        </p>
      </div>

      <ProfileClient
        profile={profile}
        userId={user.id}
        userEmail={user.email || ''}
      />
    </div>
  )
}
