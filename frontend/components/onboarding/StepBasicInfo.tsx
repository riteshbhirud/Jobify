'use client'

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface BasicInfoData {
  first_name: string
  last_name: string
  phone: string
  linkedin_url: string
  github_url: string
  portfolio_url: string
}

interface StepBasicInfoProps {
  initialData?: Partial<BasicInfoData>
  onNext: (data: BasicInfoData) => void
  loading?: boolean
}

export function StepBasicInfo({ initialData, onNext, loading }: StepBasicInfoProps) {
  const [formData, setFormData] = useState<BasicInfoData>({
    first_name: initialData?.first_name || '',
    last_name: initialData?.last_name || '',
    phone: initialData?.phone || '',
    linkedin_url: initialData?.linkedin_url || '',
    github_url: initialData?.github_url || '',
    portfolio_url: initialData?.portfolio_url || '',
  })

  const [errors, setErrors] = useState<Partial<Record<keyof BasicInfoData, string>>>({})

  const validateForm = () => {
    const newErrors: Partial<Record<keyof BasicInfoData, string>> = {}

    if (!formData.first_name.trim()) {
      newErrors.first_name = "First name is required"
    }
    if (!formData.last_name.trim()) {
      newErrors.last_name = "Last name is required"
    }
    if (formData.linkedin_url && !formData.linkedin_url.includes('linkedin.com')) {
      newErrors.linkedin_url = "Please enter a valid LinkedIn URL"
    }
    if (formData.github_url && !formData.github_url.includes('github.com')) {
      newErrors.github_url = "Please enter a valid GitHub URL"
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
    <Card className="max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Let's start with the basics</CardTitle>
        <CardDescription>
          This information will be used on your job applications
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="first_name">First Name *</Label>
              <Input
                id="first_name"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                placeholder="John"
                disabled={loading}
              />
              {errors.first_name && (
                <p className="text-sm text-destructive">{errors.first_name}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="last_name">Last Name *</Label>
              <Input
                id="last_name"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                placeholder="Doe"
                disabled={loading}
              />
              {errors.last_name && (
                <p className="text-sm text-destructive">{errors.last_name}</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone">Phone Number</Label>
            <Input
              id="phone"
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              placeholder="+1 (555) 123-4567"
              disabled={loading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="linkedin_url">LinkedIn URL</Label>
            <Input
              id="linkedin_url"
              type="url"
              value={formData.linkedin_url}
              onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })}
              placeholder="https://linkedin.com/in/johndoe"
              disabled={loading}
            />
            {errors.linkedin_url && (
              <p className="text-sm text-destructive">{errors.linkedin_url}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="github_url">GitHub URL (Optional)</Label>
            <Input
              id="github_url"
              type="url"
              value={formData.github_url}
              onChange={(e) => setFormData({ ...formData, github_url: e.target.value })}
              placeholder="https://github.com/johndoe"
              disabled={loading}
            />
            {errors.github_url && (
              <p className="text-sm text-destructive">{errors.github_url}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="portfolio_url">Portfolio/Website URL (Optional)</Label>
            <Input
              id="portfolio_url"
              type="url"
              value={formData.portfolio_url}
              onChange={(e) => setFormData({ ...formData, portfolio_url: e.target.value })}
              placeholder="https://johndoe.com"
              disabled={loading}
            />
          </div>

          <div className="flex justify-end">
            <Button type="submit" size="lg" disabled={loading}>
              {loading ? 'Saving...' : 'Continue'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
