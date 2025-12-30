import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

interface Application {
  id: string
  job_title: string
  company_name: string
  status: string
  applied_at: string
}

interface RecentApplicationsProps {
  applications: Application[]
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'applied':
      return <Badge variant="secondary">Applied ✓</Badge>
    case 'pending':
      return <Badge variant="outline">Pending</Badge>
    case 'failed':
      return <Badge variant="destructive">Failed</Badge>
    default:
      return <Badge variant="outline">{status}</Badge>
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 60) {
    return `${diffMins}m ago`
  } else if (diffHours < 24) {
    return `${diffHours}h ago`
  } else if (diffDays < 7) {
    return `${diffDays}d ago`
  } else {
    return date.toLocaleDateString()
  }
}

export function RecentApplications({ applications }: RecentApplicationsProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Recent Applications</CardTitle>
            <CardDescription>Your latest job applications</CardDescription>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/applications">View All</Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {applications.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground mb-4">No applications yet</p>
            <p className="text-sm text-muted-foreground">
              Activate automation to start applying to jobs automatically
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {applications.map((app) => (
              <div
                key={app.id}
                className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-start space-x-4 flex-1">
                  <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center text-xl">
                    🏢
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium truncate">{app.job_title}</h4>
                    <p className="text-sm text-muted-foreground">{app.company_name}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatDate(app.applied_at)}
                    </p>
                  </div>
                </div>
                <div className="ml-4">
                  {getStatusBadge(app.status)}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
