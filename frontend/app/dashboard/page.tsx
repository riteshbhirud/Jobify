// frontend/app/dashboard/page.tsx

import { redirect } from 'next/navigation'
import { createServerSupabaseClient } from '@/lib/supabase/server'
import LogoutButton from './LogoutButton'

export default async function DashboardPage() {
  const supabase = await createServerSupabaseClient()
  
  // Get authenticated user
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  // Get user profile from our users table
  const { data: profile } = await supabase
    .from('users')
    .select('*')
    .eq('id', user.id)
    .single()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-900">🚀 Job Auto Apply</h1>
          <LogoutButton />
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Welcome Card */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            👋 Hi, {profile?.first_name || user.email?.split('@')[0] || 'there'}!
          </h2>
          <p className="text-gray-600 mt-2">
            Welcome to your dashboard.
          </p>
        </div>

        {/* Profile Info */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Your Profile</h3>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Email:</span>
              <p className="font-medium">{user.email}</p>
            </div>
            <div>
              <span className="text-gray-500">User ID:</span>
              <p className="font-medium text-xs">{user.id}</p>
            </div>
            <div>
              <span className="text-gray-500">Name:</span>
              <p className="font-medium">
                {profile?.first_name && profile?.last_name 
                  ? `${profile.first_name} ${profile.last_name}`
                  : 'Not set'}
              </p>
            </div>
            <div>
              <span className="text-gray-500">Onboarding:</span>
              <p className="font-medium">
                {profile?.onboarding_completed 
                  ? '✅ Complete' 
                  : `⏳ Step ${profile?.onboarding_step || 1}`}
              </p>
            </div>
            <div>
              <span className="text-gray-500">Target Role:</span>
              <p className="font-medium">{profile?.target_role || 'Not set'}</p>
            </div>
            <div>
              <span className="text-gray-500">Automation:</span>
              <p className="font-medium">
                {profile?.is_active 
                  ? '🟢 Active' 
                  : '🔴 Inactive'}
              </p>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
          <div className="flex gap-4">
            <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
              Complete Onboarding
            </button>
            <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300">
              View Applications
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}