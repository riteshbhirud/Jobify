'use client'

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Slider } from "@/components/ui/slider"
import { Textarea } from "@/components/ui/textarea"

interface AutomationData {
  portal_password: string
  max_daily_applications: number
  min_match_score: number
  us_work_authorized: boolean
  needs_visa_sponsorship: boolean
}

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
    max_daily_applications: initialData?.max_daily_applications || 10,
    min_match_score: initialData?.min_match_score || 70,
    us_work_authorized: initialData?.us_work_authorized !== undefined ? initialData.us_work_authorized : true,
    needs_visa_sponsorship: initialData?.needs_visa_sponsorship || false,
  })

  const [errors, setErrors] = useState<Partial<Record<keyof AutomationData, string>>>({})

  const validateForm = () => {
    const newErrors: Partial<Record<keyof AutomationData, string>> = {}

    if (!formData.portal_password || formData.portal_password.length < 8) {
      newErrors.portal_password = "Password must be at least 8 characters"
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
    <Card className="max-w-3xl mx-auto">
      <CardHeader>
        <CardTitle>Almost done! Set up your automation</CardTitle>
        <CardDescription>
          Configure how we'll apply to jobs on your behalf. You can adjust these anytime.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Portal Password */}
          <div className="space-y-2">
            <Label htmlFor="portal_password">Job Portal Password *</Label>
            <div className="relative">
              <Input
                id="portal_password"
                type={showPassword ? "text" : "password"}
                value={formData.portal_password}
                onChange={(e) => setFormData({ ...formData, portal_password: e.target.value })}
                placeholder="Enter a secure password"
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
            <p className="text-xs text-muted-foreground">
              We'll use this to create accounts on job portals (Workday, Greenhouse, etc.) on your behalf.
              Use something secure but memorable.
            </p>
            {errors.portal_password && (
              <p className="text-sm text-destructive">{errors.portal_password}</p>
            )}
          </div>

          {/* Max Daily Applications */}
          <div className="space-y-3">
            <Label htmlFor="max_daily">Max Applications Per Day: {formData.max_daily_applications}</Label>
            <Slider
              id="max_daily"
              min={5}
              max={25}
              step={1}
              value={formData.max_daily_applications}
              onValueChange={(value) => setFormData({ ...formData, max_daily_applications: value })}
              disabled={loading}
            />
            <p className="text-xs text-muted-foreground">
              We recommend 10-15 to avoid overwhelming your inbox
            </p>
          </div>

          {/* Match Threshold */}
          <div className="space-y-3">
            <Label htmlFor="match_score">Match Threshold: {formData.min_match_score}%</Label>
            <Slider
              id="match_score"
              min={50}
              max={95}
              step={5}
              value={formData.min_match_score}
              onValueChange={(value) => setFormData({ ...formData, min_match_score: value })}
              disabled={loading}
            />
            <p className="text-xs text-muted-foreground">
              Higher = fewer but more relevant applications
            </p>
          </div>

          {/* Common Questions */}
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium mb-3">Common Application Questions</h3>
              <p className="text-xs text-muted-foreground mb-4">
                Pre-fill answers to frequently asked questions
              </p>
            </div>

            <div className="space-y-3">
              <Label>Are you authorized to work in the US?</Label>
              <div className="flex gap-6">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="us_work_authorized"
                    checked={formData.us_work_authorized === true}
                    onChange={() => setFormData({
                      ...formData,
                      us_work_authorized: true
                    })}
                    disabled={loading}
                    className="w-4 h-4 text-primary border-gray-300 focus:ring-primary"
                  />
                  <span className="text-sm font-medium">Yes</span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="us_work_authorized"
                    checked={formData.us_work_authorized === false}
                    onChange={() => setFormData({
                      ...formData,
                      us_work_authorized: false
                    })}
                    disabled={loading}
                    className="w-4 h-4 text-primary border-gray-300 focus:ring-primary"
                  />
                  <span className="text-sm font-medium">No</span>
                </label>
              </div>
            </div>

            <div className="space-y-3">
              <Label>Will you require visa sponsorship?</Label>
              <div className="flex gap-6">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="needs_visa_sponsorship"
                    checked={formData.needs_visa_sponsorship === true}
                    onChange={() => setFormData({
                      ...formData,
                      needs_visa_sponsorship: true
                    })}
                    disabled={loading}
                    className="w-4 h-4 text-primary border-gray-300 focus:ring-primary"
                  />
                  <span className="text-sm font-medium">Yes</span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="needs_visa_sponsorship"
                    checked={formData.needs_visa_sponsorship === false}
                    onChange={() => setFormData({
                      ...formData,
                      needs_visa_sponsorship: false
                    })}
                    disabled={loading}
                    className="w-4 h-4 text-primary border-gray-300 focus:ring-primary"
                  />
                  <span className="text-sm font-medium">No</span>
                </label>
              </div>
            </div>
          </div>

          <div className="flex justify-between">
            <Button type="button" variant="outline" onClick={onBack} disabled={loading}>
              Back
            </Button>
            <Button type="submit" size="lg" disabled={loading}>
              {loading ? 'Completing...' : 'Complete Setup'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
