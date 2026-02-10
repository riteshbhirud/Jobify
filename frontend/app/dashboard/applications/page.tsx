import { redirect } from 'next/navigation'
import { createServerSupabaseClient } from '@/lib/supabase/server'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export const dynamic = 'force-dynamic'

function getStatusBadge(status: string) {
  switch (status) {
    case 'submitted':
      return <Badge className="bg-green-500/10 text-green-600 border-green-500/20">Submitted</Badge>
    case 'started':
      return <Badge className="bg-blue-500/10 text-blue-600 border-blue-500/20">In Progress</Badge>
    case 'queued':
      return <Badge className="bg-yellow-500/10 text-yellow-600 border-yellow-500/20">Queued</Badge>
    case 'matched':
      return <Badge className="bg-purple-500/10 text-purple-600 border-purple-500/20">Matched</Badge>
    case 'failed':
      return <Badge variant="destructive">Failed</Badge>
    default:
      return <Badge variant="outline">{status}</Badge>
  }
}

function formatDate(dateString: string | null) {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

export default async function ApplicationsPage() {
  const supabase = await createServerSupabaseClient()

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  const { data: applications } = await supabase
    .from('applications')
    .select('id, status, match_score, submitted_at, created_at, last_error, jobs(title, company, location)')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })

  const apps = applications || []

  // Count by status
  const statusCounts: Record<string, number> = {}
  apps.forEach((app: any) => {
    statusCounts[app.status] = (statusCounts[app.status] || 0) + 1
  })

  return (
    <div className="container mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Applications</h1>
        <p className="text-muted-foreground">
          View and manage all your job applications
        </p>
      </div>

      {apps.length > 0 && (
        <div className="flex flex-wrap gap-3 mb-6">
          <Badge variant="outline" className="text-sm py-1 px-3">
            Total: {apps.length}
          </Badge>
          {statusCounts['submitted'] && (
            <Badge className="bg-green-500/10 text-green-600 border-green-500/20 text-sm py-1 px-3">
              Submitted: {statusCounts['submitted']}
            </Badge>
          )}
          {statusCounts['queued'] && (
            <Badge className="bg-yellow-500/10 text-yellow-600 border-yellow-500/20 text-sm py-1 px-3">
              Queued: {statusCounts['queued']}
            </Badge>
          )}
          {statusCounts['matched'] && (
            <Badge className="bg-purple-500/10 text-purple-600 border-purple-500/20 text-sm py-1 px-3">
              Matched: {statusCounts['matched']}
            </Badge>
          )}
          {statusCounts['failed'] && (
            <Badge variant="destructive" className="text-sm py-1 px-3">
              Failed: {statusCounts['failed']}
            </Badge>
          )}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>All Applications</CardTitle>
          <CardDescription>
            Your complete application history
          </CardDescription>
        </CardHeader>
        <CardContent>
          {apps.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">📭</div>
              <h3 className="text-lg font-medium mb-2">No applications yet</h3>
              <p className="text-muted-foreground mb-6">
                Activate automation from your dashboard to start applying to jobs automatically
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {apps.map((app: any) => (
                <div
                  key={app.id}
                  className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start space-x-4 flex-1">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center text-xl flex-shrink-0">
                      🏢
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium truncate">{app.jobs?.title || 'Unknown Position'}</h4>
                      <p className="text-sm text-muted-foreground">{app.jobs?.company || 'Unknown Company'}</p>
                      <div className="flex items-center gap-3 mt-1">
                        {app.jobs?.location && (
                          <p className="text-xs text-muted-foreground">{app.jobs.location}</p>
                        )}
                        {app.match_score && (
                          <p className="text-xs text-muted-foreground">
                            Match: {Math.round(app.match_score * 100)}%
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground">
                          {formatDate(app.submitted_at || app.created_at)}
                        </p>
                      </div>
                      {app.status === 'failed' && app.last_error && (
                        <p className="text-xs text-destructive mt-1 truncate">{app.last_error}</p>
                      )}
                    </div>
                  </div>
                  <div className="ml-4 flex-shrink-0">
                    {getStatusBadge(app.status)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
