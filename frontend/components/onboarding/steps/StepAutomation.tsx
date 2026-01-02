'use client'

import { useState } from 'react'
import { Zap, Eye, EyeOff, Lock, Shield, CheckCircle2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AutomationData } from '../types'

interface StepAutomationProps {
  initialData?: Partial<AutomationData>
  onNext: (data: AutomationData) => void
  onBack: () => void
  loading?: boolean
}

export function StepAutomation({ initialData, onNext, onBack, loading }: StepAutomationProps) {
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState<AutomationData>({
    portal_password: initialData?.portal_password || '',
  })

  const [errors, setErrors] = useState<Partial<Record<keyof AutomationData, string>>>({})

  const validateForm = () => {
    const newErrors: Partial<Record<keyof AutomationData, string>> = {}

    if (!formData.portal_password || formData.portal_password.length < 8) {
      newErrors.portal_password = 'Password must be at least 8 characters'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      onNext(formData)
    }
  }

  return (
    <Card className="max-w-3xl mx-auto shadow-lg border-0 bg-card/80 backdrop-blur">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mb-4">
          <Zap className="h-7 w-7 text-primary" />
        </div>
        <CardTitle className="text-2xl">Automation Settings</CardTitle>
        <CardDescription className="text-base">
          Set up your portal password to enable automated applications
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Portal Password Section */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="portal_password" className="flex items-center gap-2 text-base">
                <Lock className="h-4 w-4" />
                Job Portal Password *
              </Label>
              <div className="relative">
                <Input
                  id="portal_password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.portal_password}
                  onChange={(e) => setFormData({ ...formData, portal_password: e.target.value })}
                  placeholder="Enter a secure password"
                  disabled={loading}
                  className="pr-10 h-12 bg-background"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.portal_password && (
                <p className="text-sm text-destructive">{errors.portal_password}</p>
              )}
            </div>

            <div className="bg-muted/50 rounded-xl p-4 space-y-3">
              <p className="text-sm text-muted-foreground">
                This password will be used when creating accounts on job portals like Workday, Greenhouse, Lever, and others.
              </p>
              <div className="flex items-start gap-2 text-sm">
                <Shield className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                <span className="text-muted-foreground">
                  Choose something secure but memorable - you may need it later.
                </span>
              </div>
            </div>
          </div>

          {/* What happens next */}
          <div className="border rounded-xl p-5 space-y-4 bg-gradient-to-br from-green-50/50 to-transparent dark:from-green-950/20">
            <h4 className="font-semibold flex items-center gap-2 text-green-700 dark:text-green-400">
              <CheckCircle2 className="h-5 w-5" />
              What happens after setup
            </h4>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-medium">1.</span>
                We'll analyze job postings that match your preferences
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-medium">2.</span>
                Our AI will auto-fill applications using your profile
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-medium">3.</span>
                You'll receive notifications for each application submitted
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-600 font-medium">4.</span>
                Track all your applications from your dashboard
              </li>
            </ul>
          </div>

          {/* Navigation */}
          <div className="flex justify-between pt-6">
            <Button type="button" variant="ghost" onClick={onBack} disabled={loading}>
              Back
            </Button>
            <Button type="submit" disabled={loading} className="px-8">
              {loading ? 'Completing Setup...' : 'Complete Setup'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
