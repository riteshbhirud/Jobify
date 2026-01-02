'use client'

import { useState } from 'react'
import { Target, Building2, DollarSign, Briefcase } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { TagInput } from '../shared/TagInput'
import { PreferencesData } from '../types'

interface StepPreferencesProps {
  initialData?: Partial<PreferencesData>
  onNext: (data: PreferencesData) => void
  onBack: () => void
  loading?: boolean
}

export function StepPreferences({ initialData, onNext, onBack, loading }: StepPreferencesProps) {
  const [formData, setFormData] = useState<PreferencesData>({
    target_role: initialData?.target_role || '',
    target_type: initialData?.target_type || 'both',
    locations: initialData?.locations || [],
    remote_preference: initialData?.remote_preference || 'any',
    experience_level: initialData?.experience_level || '',
    min_salary: initialData?.min_salary || undefined,
    excluded_companies: initialData?.excluded_companies || [],
    preferred_companies: initialData?.preferred_companies || [],
  })

  const [errors, setErrors] = useState<Partial<Record<keyof PreferencesData, string>>>({})

  const validateForm = () => {
    const newErrors: Partial<Record<keyof PreferencesData, string>> = {}

    if (!formData.target_role.trim()) {
      newErrors.target_role = 'Target role is required'
    }
    if (!formData.target_type) {
      newErrors.target_type = 'Job type is required'
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
          <Target className="h-7 w-7 text-primary" />
        </div>
        <CardTitle className="text-2xl">Job Preferences</CardTitle>
        <CardDescription className="text-base">
          Tell us what you're looking for. The more specific, the better we can match you.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Target Role Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <Briefcase className="h-4 w-4 text-primary" />
              <h3 className="font-medium">What are you looking for?</h3>
            </div>

            <div className="space-y-2">
              <Label htmlFor="target_role">Target Role *</Label>
              <Input
                id="target_role"
                value={formData.target_role}
                onChange={(e) => setFormData({ ...formData, target_role: e.target.value })}
                placeholder="e.g., Software Engineer, Product Manager, Data Scientist"
                disabled={loading}
                className="bg-background"
              />
              {errors.target_role && (
                <p className="text-sm text-destructive">{errors.target_role}</p>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="target_type">Job Type *</Label>
                <Select
                  value={formData.target_type}
                  onValueChange={(value) => setFormData({ ...formData, target_type: value })}
                  disabled={loading}
                >
                  <SelectTrigger id="target_type" className="bg-background">
                    <SelectValue placeholder="Select job type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="internship">Internship</SelectItem>
                    <SelectItem value="full_time">Full-time</SelectItem>
                    <SelectItem value="contract">Contract</SelectItem>
                    <SelectItem value="both">Both Internship & Full-time</SelectItem>
                  </SelectContent>
                </Select>
                {errors.target_type && (
                  <p className="text-sm text-destructive">{errors.target_type}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="experience_level">Experience Level</Label>
                <Select
                  value={formData.experience_level}
                  onValueChange={(value) => setFormData({ ...formData, experience_level: value })}
                  disabled={loading}
                >
                  <SelectTrigger id="experience_level" className="bg-background">
                    <SelectValue placeholder="Select level" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="intern">Intern / Entry Level</SelectItem>
                    <SelectItem value="junior">Junior (0-2 years)</SelectItem>
                    <SelectItem value="mid">Mid-Level (2-5 years)</SelectItem>
                    <SelectItem value="senior">Senior (5-10 years)</SelectItem>
                    <SelectItem value="lead">Lead / Staff (10+ years)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Salary Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <DollarSign className="h-4 w-4 text-primary" />
              <h3 className="font-medium">Compensation</h3>
            </div>

            <div className="space-y-2">
              <Label htmlFor="min_salary">Minimum Salary (Annual, Optional)</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  $
                </span>
                <Input
                  id="min_salary"
                  type="number"
                  value={formData.min_salary || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      min_salary: e.target.value ? Number(e.target.value) : undefined,
                    })
                  }
                  placeholder="80000"
                  className="pl-7 bg-background"
                  disabled={loading}
                />
              </div>
              {formData.min_salary && (
                <p className="text-sm text-muted-foreground">
                  ${formData.min_salary.toLocaleString()} per year
                </p>
              )}
            </div>
          </div>

          {/* Company Preferences Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <Building2 className="h-4 w-4 text-primary" />
              <h3 className="font-medium">Company Preferences (Optional)</h3>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  Preferred Companies
                </Label>
                <TagInput
                  tags={formData.preferred_companies}
                  onTagsChange={(preferred_companies) =>
                    setFormData({ ...formData, preferred_companies })
                  }
                  placeholder="Companies you'd like to prioritize"
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  We'll prioritize applications to these companies
                </p>
              </div>

              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                  Excluded Companies
                </Label>
                <TagInput
                  tags={formData.excluded_companies}
                  onTagsChange={(excluded_companies) =>
                    setFormData({ ...formData, excluded_companies })
                  }
                  placeholder="Companies you don't want to apply to"
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  We'll skip jobs from these companies
                </p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex justify-between pt-6">
            <Button type="button" variant="ghost" onClick={onBack} disabled={loading}>
              Back
            </Button>
            <Button type="submit" disabled={loading} className="px-8">
              {loading ? 'Saving...' : 'Continue'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
