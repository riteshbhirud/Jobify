import { redirect } from 'next/navigation'
import { createServerSupabaseClient } from '@/lib/supabase/server'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

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

        <div className="space-y-6">
          {/* Basic Info */}
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>Your personal details</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">First Name</p>
                  <p className="font-medium">{profile?.first_name || 'Not set'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Last Name</p>
                  <p className="font-medium">{profile?.last_name || 'Not set'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Email</p>
                  <p className="font-medium">{user.email}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Phone</p>
                  <p className="font-medium">{profile?.phone || 'Not set'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Job Preferences */}
          <Card>
            <CardHeader>
              <CardTitle>Job Preferences</CardTitle>
              <CardDescription>Your job search criteria</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground mb-2">Target Role</p>
                <p className="font-medium">{profile?.target_role || 'Not set'}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-2">Preferred Locations</p>
                <div className="flex flex-wrap gap-2">
                  {profile?.locations && profile.locations.length > 0 ? (
                    profile.locations.map((location: string) => (
                      <Badge key={location} variant="secondary">{location}</Badge>
                    ))
                  ) : (
                    <span className="text-muted-foreground">Not set</span>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Job Type</p>
                  <p className="font-medium capitalize">{profile?.target_type?.replace('_', '-') || 'Not set'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Remote Preference</p>
                  <p className="font-medium capitalize">{profile?.remote_preference || 'Not set'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Automation Settings */}
          <Card>
            <CardHeader>
              <CardTitle>Automation Settings</CardTitle>
              <CardDescription>Your application automation configuration</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Max Daily Applications</p>
                  <p className="font-medium">{profile?.max_daily_applications || 10}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Match Threshold</p>
                  <p className="font-medium">{profile?.min_match_score || 70}%</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
  )
}
