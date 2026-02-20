'use client'

import { useState, useEffect } from 'react'
import { Pencil, Target, Briefcase, DollarSign, Building2, MapPin } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { TagInput } from '@/components/onboarding/shared/TagInput'
import { PreferencesData } from '@/components/onboarding/types'

interface PreferencesSectionProps {
  profile: any
  isEditing: boolean
  onEdit: () => void
  onSave: (data: Record<string, any>) => Promise<void>
  onCancel: () => void
  saving: boolean
}

export function PreferencesSection({
  profile,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  saving,
}: PreferencesSectionProps) {
  const [formData, setFormData] = useState<PreferencesData>({
    target_role: profile?.target_role || '',
    target_type: profile?.target_type || 'both',
    locations: profile?.locations || [],
    remote_preference: profile?.remote_preference || 'any',
    experience_level: profile?.experience_level || '',
    min_salary: profile?.min_salary || undefined,
    excluded_companies: profile?.excluded_companies || [],
    preferred_companies: profile?.preferred_companies || [],
  })

  const [errors, setErrors] = useState<Partial<Record<keyof PreferencesData, string>>>({})

  useEffect(() => {
    if (!isEditing) {
      setFormData({
        target_role: profile?.target_role || '',
        target_type: profile?.target_type || 'both',
        locations: profile?.locations || [],
        remote_preference: profile?.remote_preference || 'any',
        experience_level: profile?.experience_level || '',
        min_salary: profile?.min_salary || undefined,
        excluded_companies: profile?.excluded_companies || [],
        preferred_companies: profile?.preferred_companies || [],
      })
      setErrors({})
    }
  }, [profile, isEditing])

  const validateForm = () => {
    const newErrors: Partial<Record<keyof PreferencesData, string>> = {}
    if (!formData.target_role.trim()) newErrors.target_role = 'Target role is required'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateForm()) return
    await onSave(formData)
  }

  if (!isEditing) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div>
            <CardTitle>Job Preferences</CardTitle>
            <CardDescription>Your job search criteria</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onEdit}>
            <Pencil className="h-4 w-4 mr-1" />
            Edit
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Target Role</p>
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
                <span className="text-muted-foreground text-sm">Not set</span>
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
            <div>
              <p className="text-sm text-muted-foreground">Experience Level</p>
              <p className="font-medium capitalize">{profile?.experience_level || 'Not set'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Min Salary</p>
              <p className="font-medium">
                {profile?.min_salary ? `$${profile.min_salary.toLocaleString()}/yr` : 'Not set'}
              </p>
            </div>
          </div>

          {(profile?.preferred_companies?.length > 0 || profile?.excluded_companies?.length > 0) && (
            <div className="space-y-3">
              {profile?.preferred_companies?.length > 0 && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Preferred Companies</p>
                  <div className="flex flex-wrap gap-1">
                    {profile.preferred_companies.map((c: string) => (
                      <Badge key={c} variant="secondary" className="text-xs">{c}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {profile?.excluded_companies?.length > 0 && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Excluded Companies</p>
                  <div className="flex flex-wrap gap-1">
                    {profile.excluded_companies.map((c: string) => (
                      <Badge key={c} variant="outline" className="text-xs">{c}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Edit Job Preferences</CardTitle>
        <CardDescription>
          Changes to these settings will update your job matching profile
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-8">
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <Briefcase className="h-4 w-4 text-primary" />
              <h3 className="font-medium text-sm">What are you looking for?</h3>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit_target_role">Target Role *</Label>
              <Input
                id="edit_target_role"
                value={formData.target_role}
                onChange={(e) => setFormData({ ...formData, target_role: e.target.value })}
                placeholder="e.g., Software Engineer, Product Manager"
                disabled={saving}
              />
              {errors.target_role && <p className="text-sm text-destructive">{errors.target_role}</p>}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Job Type</Label>
                <Select
                  value={formData.target_type}
                  onValueChange={(value) => setFormData({ ...formData, target_type: value })}
                  disabled={saving}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="internship">Internship</SelectItem>
                    <SelectItem value="full_time">Full-time</SelectItem>
                    <SelectItem value="contract">Contract</SelectItem>
                    <SelectItem value="both">Both Internship & Full-time</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Experience Level</Label>
                <Select
                  value={formData.experience_level}
                  onValueChange={(value) => setFormData({ ...formData, experience_level: value })}
                  disabled={saving}
                >
                  <SelectTrigger>
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

            <div className="space-y-2">
              <Label>Preferred Locations</Label>
              <TagInput
                tags={formData.locations}
                onTagsChange={(locations) => setFormData({ ...formData, locations })}
                placeholder="Add a location (e.g., San Francisco, CA)"
                disabled={saving}
              />
            </div>

            <div className="space-y-2">
              <Label>Remote Preference</Label>
              <Select
                value={formData.remote_preference}
                onValueChange={(value) => setFormData({ ...formData, remote_preference: value })}
                disabled={saving}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="remote">Remote Only</SelectItem>
                  <SelectItem value="hybrid">Hybrid</SelectItem>
                  <SelectItem value="onsite">On-site</SelectItem>
                  <SelectItem value="any">Any</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <DollarSign className="h-4 w-4 text-primary" />
              <h3 className="font-medium text-sm">Compensation</h3>
            </div>
            <div className="space-y-2">
              <Label>Minimum Salary (Annual)</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                <Input
                  type="number"
                  value={formData.min_salary || ''}
                  onChange={(e) => setFormData({ ...formData, min_salary: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="80000"
                  className="pl-7"
                  disabled={saving}
                />
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <Building2 className="h-4 w-4 text-primary" />
              <h3 className="font-medium text-sm">Company Preferences</h3>
            </div>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  Preferred Companies
                </Label>
                <TagInput
                  tags={formData.preferred_companies}
                  onTagsChange={(preferred_companies) => setFormData({ ...formData, preferred_companies })}
                  placeholder="Companies you'd like to prioritize"
                  disabled={saving}
                />
              </div>
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                  Excluded Companies
                </Label>
                <TagInput
                  tags={formData.excluded_companies}
                  onTagsChange={(excluded_companies) => setFormData({ ...formData, excluded_companies })}
                  placeholder="Companies you don't want to apply to"
                  disabled={saving}
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
