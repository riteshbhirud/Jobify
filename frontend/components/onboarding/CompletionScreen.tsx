'use client'

import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  CheckCircle2,
  Briefcase,
  MapPin,
  GraduationCap,
  Zap,
  ArrowRight,
} from 'lucide-react'

interface CompletionScreenProps {
  userData: {
    first_name?: string
    target_role?: string
    locations?: string[]
    education?: Array<{ school: string; degree: string }>
    experience?: Array<{ company: string; title: string }>
    skills?: string[]
    max_daily_applications?: number
    min_match_score?: number
  }
}

export function CompletionScreen({ userData }: CompletionScreenProps) {
  const router = useRouter()

  const summaryItems = [
    {
      icon: Briefcase,
      label: 'Target Role',
      value: userData.target_role || 'Not specified',
    },
    {
      icon: MapPin,
      label: 'Locations',
      value:
        userData.locations && userData.locations.length > 0
          ? userData.locations.slice(0, 3).join(', ') +
            (userData.locations.length > 3 ? ` +${userData.locations.length - 3} more` : '')
          : 'Not specified',
    },
    {
      icon: GraduationCap,
      label: 'Education',
      value:
        userData.education && userData.education.length > 0
          ? `${userData.education.length} ${userData.education.length === 1 ? 'entry' : 'entries'}`
          : 'Not added',
    },
    {
      icon: Zap,
      label: 'Daily Applications',
      value: `Up to ${userData.max_daily_applications || 10}/day`,
    },
  ]

  return (
    <div className="max-w-2xl mx-auto text-center space-y-8">
      {/* Success Animation */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15 }}
        className="flex justify-center"
      >
        <div className="w-24 h-24 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
          <CheckCircle2 className="h-14 w-14 text-green-600 dark:text-green-400" />
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <h1 className="text-3xl md:text-4xl font-bold mb-3">
          You're All Set{userData.first_name ? `, ${userData.first_name}` : ''}!
        </h1>
        <p className="text-lg text-muted-foreground">
          Your profile is complete. You're ready to start your automated job search.
        </p>
      </motion.div>

      {/* Summary Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <Card className="text-left">
          <CardHeader>
            <CardTitle>Your Profile Summary</CardTitle>
            <CardDescription>
              You can adjust these settings anytime from your dashboard
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-1">
            {summaryItems.map((item, index) => (
              <div
                key={item.label}
                className="flex items-center justify-between py-3 border-b last:border-b-0"
              >
                <div className="flex items-center gap-3">
                  <item.icon className="h-5 w-5 text-muted-foreground" />
                  <span className="text-muted-foreground">{item.label}</span>
                </div>
                <span className="font-medium text-right">{item.value}</span>
              </div>
            ))}

            {/* Skills Preview */}
            {userData.skills && userData.skills.length > 0 && (
              <div className="pt-3">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-muted-foreground">Skills</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {userData.skills.slice(0, 6).map((skill) => (
                    <span
                      key={skill}
                      className="px-2 py-1 bg-primary/10 text-primary text-sm rounded-md"
                    >
                      {skill}
                    </span>
                  ))}
                  {userData.skills.length > 6 && (
                    <span className="px-2 py-1 bg-muted text-muted-foreground text-sm rounded-md">
                      +{userData.skills.length - 6} more
                    </span>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* What's Next */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-muted/50 rounded-lg p-6 text-left"
      >
        <h3 className="font-semibold mb-3">What's Next?</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li className="flex items-start gap-2">
            <span className="text-primary font-medium">1.</span>
            Head to your dashboard to review your settings
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary font-medium">2.</span>
            Toggle the automation switch to start applying
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary font-medium">3.</span>
            Track your applications and interviews in real-time
          </li>
        </ul>
      </motion.div>

      {/* CTA Button */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <Button
          size="lg"
          className="text-lg px-8 py-6 gap-2"
          onClick={() => router.push('/dashboard')}
        >
          Go to Dashboard
          <ArrowRight className="h-5 w-5" />
        </Button>
      </motion.div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="text-sm text-muted-foreground"
      >
        Your automation is currently paused. Activate it from your dashboard when you're ready.
      </motion.p>
    </div>
  )
}
