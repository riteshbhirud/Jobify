'use client'

import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface CompletionScreenProps {
  userData: {
    target_role?: string
    locations?: string[]
    max_daily_applications?: number
  }
}

export function CompletionScreen({ userData }: CompletionScreenProps) {
  const router = useRouter()

  return (
    <div className="max-w-2xl mx-auto text-center space-y-8">
      {/* Success Animation */}
      <div className="text-8xl animate-bounce">🎉</div>

      <div>
        <h1 className="text-4xl font-bold mb-4">You're All Set!</h1>
        <p className="text-xl text-muted-foreground">
          Your job search is now on autopilot. Relax!
        </p>
      </div>

      {/* Summary Card */}
      <Card className="text-left">
        <CardHeader>
          <CardTitle>Your Configuration Summary</CardTitle>
          <CardDescription>You can adjust these settings anytime from your dashboard</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between items-center py-2 border-b">
            <span className="text-muted-foreground">Target Role:</span>
            <span className="font-medium">{userData.target_role || 'Not specified'}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b">
            <span className="text-muted-foreground">Locations:</span>
            <span className="font-medium">
              {userData.locations && userData.locations.length > 0
                ? userData.locations.join(', ')
                : 'Not specified'}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b">
            <span className="text-muted-foreground">Daily Applications:</span>
            <span className="font-medium">Up to {userData.max_daily_applications || 10}/day</span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="text-muted-foreground">Status:</span>
            <span className="font-medium text-secondary">✓ Ready to activate</span>
          </div>
        </CardContent>
      </Card>

      {/* CTA */}
      <Button size="lg" className="text-lg px-8 py-6" onClick={() => router.push('/dashboard')}>
        Go to Dashboard
      </Button>

      <p className="text-sm text-muted-foreground">
        Click the toggle in your dashboard to start auto-applying!
      </p>
    </div>
  )
}
