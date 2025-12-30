'use client'

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"

interface PreferencesData {
  target_role: string
  target_type: string
  locations: string[]
  remote_preference: string
  experience_level: string
  min_salary?: number
  needs_visa_sponsorship: boolean
  excluded_companies: string[]
  preferred_companies: string[]
}

interface StepPreferencesProps {
  initialData?: Partial<PreferencesData>
  onNext: (data: PreferencesData) => void
  onBack: () => void
  loading?: boolean
}

export function StepPreferences({ initialData, onNext, onBack, loading }: StepPreferencesProps) {
  const [formData, setFormData] = useState<PreferencesData>({
    target_role: initialData?.target_role || '',
    target_type: initialData?.target_type || '',
    locations: initialData?.locations || [],
    remote_preference: initialData?.remote_preference || '',
    experience_level: initialData?.experience_level || '',
    min_salary: initialData?.min_salary || undefined,
    needs_visa_sponsorship: initialData?.needs_visa_sponsorship || false,
    excluded_companies: initialData?.excluded_companies || [],
    preferred_companies: initialData?.preferred_companies || [],
  })

  const [newLocation, setNewLocation] = useState('')
  const [newExcluded, setNewExcluded] = useState('')
  const [newPreferred, setNewPreferred] = useState('')
  const [errors, setErrors] = useState<Partial<Record<keyof PreferencesData, string>>>({})

  const addLocation = () => {
    if (newLocation.trim() && !formData.locations.includes(newLocation.trim())) {
      setFormData({ ...formData, locations: [...formData.locations, newLocation.trim()] })
      setNewLocation('')
    }
  }

  const removeLocation = (location: string) => {
    setFormData({ ...formData, locations: formData.locations.filter(l => l !== location) })
  }

  const addExcluded = () => {
    if (newExcluded.trim() && !formData.excluded_companies.includes(newExcluded.trim())) {
      setFormData({ ...formData, excluded_companies: [...formData.excluded_companies, newExcluded.trim()] })
      setNewExcluded('')
    }
  }

  const removeExcluded = (company: string) => {
    setFormData({ ...formData, excluded_companies: formData.excluded_companies.filter(c => c !== company) })
  }

  const addPreferred = () => {
    if (newPreferred.trim() && !formData.preferred_companies.includes(newPreferred.trim())) {
      setFormData({ ...formData, preferred_companies: [...formData.preferred_companies, newPreferred.trim()] })
      setNewPreferred('')
    }
  }

  const removePreferred = (company: string) => {
    setFormData({ ...formData, preferred_companies: formData.preferred_companies.filter(c => c !== company) })
  }

  const validateForm = () => {
    const newErrors: Partial<Record<keyof PreferencesData, string>> = {}

    if (!formData.target_role.trim()) {
      newErrors.target_role = "Target role is required"
    }
    if (!formData.target_type) {
      newErrors.target_type = "Job type is required"
    }
    if (formData.locations.length === 0) {
      newErrors.locations = "Add at least one location"
    }
    if (!formData.remote_preference) {
      newErrors.remote_preference = "Remote preference is required"
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
        <CardTitle>What's your dream job?</CardTitle>
        <CardDescription>
          The more specific you are, the better we can match you with opportunities
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="target_role">Target Role *</Label>
            <Input
              id="target_role"
              value={formData.target_role}
              onChange={(e) => setFormData({ ...formData, target_role: e.target.value })}
              placeholder="e.g., Software Engineer, Product Manager"
              disabled={loading}
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
                <SelectTrigger id="target_type">
                  <SelectValue placeholder="Select job type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="internship">Internship</SelectItem>
                  <SelectItem value="full_time">Full-time</SelectItem>
                  <SelectItem value="both">Both</SelectItem>
                </SelectContent>
              </Select>
              {errors.target_type && (
                <p className="text-sm text-destructive">{errors.target_type}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="remote_preference">Remote Preference *</Label>
              <Select
                value={formData.remote_preference}
                onValueChange={(value) => setFormData({ ...formData, remote_preference: value })}
                disabled={loading}
              >
                <SelectTrigger id="remote_preference">
                  <SelectValue placeholder="Select preference" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="remote">Remote Only</SelectItem>
                  <SelectItem value="hybrid">Hybrid OK</SelectItem>
                  <SelectItem value="onsite">On-site OK</SelectItem>
                  <SelectItem value="any">Any</SelectItem>
                </SelectContent>
              </Select>
              {errors.remote_preference && (
                <p className="text-sm text-destructive">{errors.remote_preference}</p>
              )}
            </div>
          </div>

          <div className="space-y-3">
            <Label>Preferred Locations *</Label>
            <div className="flex gap-2">
              <Input
                value={newLocation}
                onChange={(e) => setNewLocation(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addLocation()
                  }
                }}
                placeholder="e.g., San Francisco, Remote, New York"
                disabled={loading}
              />
              <Button type="button" onClick={addLocation} variant="outline" disabled={loading}>
                Add
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {formData.locations.map((location) => (
                <Badge key={location} variant="secondary" className="px-3 py-1">
                  {location}
                  <button
                    type="button"
                    onClick={() => removeLocation(location)}
                    className="ml-2 hover:text-destructive"
                    disabled={loading}
                  >
                    ×
                  </button>
                </Badge>
              ))}
            </div>
            {errors.locations && (
              <p className="text-sm text-destructive">{errors.locations}</p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="experience_level">Experience Level</Label>
              <Select
                value={formData.experience_level}
                onValueChange={(value) => setFormData({ ...formData, experience_level: value })}
                disabled={loading}
              >
                <SelectTrigger id="experience_level">
                  <SelectValue placeholder="Select level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0-2">0-2 years</SelectItem>
                  <SelectItem value="2-5">2-5 years</SelectItem>
                  <SelectItem value="5-10">5-10 years</SelectItem>
                  <SelectItem value="10+">10+ years</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="min_salary">Minimum Salary (Optional)</Label>
              <div className="space-y-2">
                <Input
                  id="min_salary"
                  type="number"
                  value={formData.min_salary || ''}
                  onChange={(e) => setFormData({ ...formData, min_salary: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="e.g., 80000"
                  disabled={loading}
                />
                {formData.min_salary && (
                  <p className="text-xs text-muted-foreground">
                    ${formData.min_salary.toLocaleString()}/year
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="visa"
                checked={formData.needs_visa_sponsorship}
                onChange={(e) => setFormData({ ...formData, needs_visa_sponsorship: e.target.checked })}
                className="rounded border-input"
                disabled={loading}
              />
              <Label htmlFor="visa" className="cursor-pointer">
                I require visa sponsorship
              </Label>
            </div>
          </div>

          <div className="space-y-3">
            <Label>Companies to Exclude (Optional)</Label>
            <div className="flex gap-2">
              <Input
                value={newExcluded}
                onChange={(e) => setNewExcluded(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addExcluded()
                  }
                }}
                placeholder="Companies you don't want to apply to"
                disabled={loading}
              />
              <Button type="button" onClick={addExcluded} variant="outline" disabled={loading}>
                Add
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {formData.excluded_companies.map((company) => (
                <Badge key={company} variant="destructive" className="px-3 py-1">
                  {company}
                  <button
                    type="button"
                    onClick={() => removeExcluded(company)}
                    className="ml-2 hover:text-white"
                    disabled={loading}
                  >
                    ×
                  </button>
                </Badge>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <Label>Preferred Companies (Optional)</Label>
            <div className="flex gap-2">
              <Input
                value={newPreferred}
                onChange={(e) => setNewPreferred(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addPreferred()
                  }
                }}
                placeholder="Companies you'd like to prioritize"
                disabled={loading}
              />
              <Button type="button" onClick={addPreferred} variant="outline" disabled={loading}>
                Add
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {formData.preferred_companies.map((company) => (
                <Badge key={company} className="px-3 py-1">
                  {company}
                  <button
                    type="button"
                    onClick={() => removePreferred(company)}
                    className="ml-2 hover:text-destructive"
                    disabled={loading}
                  >
                    ×
                  </button>
                </Badge>
              ))}
            </div>
          </div>

          <div className="flex justify-between">
            <Button type="button" variant="outline" onClick={onBack} disabled={loading}>
              Back
            </Button>
            <Button type="submit" size="lg" disabled={loading}>
              {loading ? 'Saving...' : 'Continue'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
