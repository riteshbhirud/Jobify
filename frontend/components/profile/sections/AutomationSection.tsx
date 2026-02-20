'use client'

import { useState, useEffect } from 'react'
import { Pencil, Zap, Eye, EyeOff, Lock } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface AutomationSectionProps {
  profile: any
  isEditing: boolean
  onEdit: () => void
  onSave: (data: Record<string, any>) => Promise<void>
  onCancel: () => void
  saving: boolean
}

export function AutomationSection({
  profile,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  saving,
}: AutomationSectionProps) {
  const [maxDaily, setMaxDaily] = useState(profile?.max_daily_applications || 10)
  const [portalPassword, setPortalPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!isEditing) {
      setMaxDaily(profile?.max_daily_applications || 10)
      setPortalPassword('')
      setErrors({})
    }
  }, [profile, isEditing])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const newErrors: Record<string, string> = {}
    if (portalPassword && portalPassword.length < 8) {
      newErrors.portal_password = 'Password must be at least 8 characters'
    }
    if (maxDaily < 1 || maxDaily > 100) {
      newErrors.max_daily = 'Must be between 1 and 100'
    }
    setErrors(newErrors)
    if (Object.keys(newErrors).length > 0) return

    const data: Record<string, any> = { max_daily_applications: maxDaily }
    if (portalPassword) {
      data.portal_password = portalPassword
    }
    await onSave(data)
  }

  if (!isEditing) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div>
            <CardTitle>Automation Settings</CardTitle>
            <CardDescription>Your application automation configuration</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onEdit}>
            <Pencil className="h-4 w-4 mr-1" />
            Edit
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Max Daily Applications</p>
              <p className="font-medium">{profile?.max_daily_applications || 10}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Match Threshold</p>
              <p className="font-medium">{profile?.min_match_score || 70}%</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Portal Password</p>
              <p className="font-medium">{profile?.portal_password ? '••••••••' : 'Not set'}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Edit Automation Settings</CardTitle>
        <CardDescription>Update your automation configuration</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="edit_max_daily">Max Daily Applications</Label>
            <Input
              id="edit_max_daily"
              type="number"
              min={1}
              max={100}
              value={maxDaily}
              onChange={(e) => setMaxDaily(Number(e.target.value))}
              disabled={saving}
            />
            {errors.max_daily && <p className="text-sm text-destructive">{errors.max_daily}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit_portal_password" className="flex items-center gap-2">
              <Lock className="h-4 w-4" />
              Portal Password
            </Label>
            <div className="relative">
              <Input
                id="edit_portal_password"
                type={showPassword ? 'text' : 'password'}
                value={portalPassword}
                onChange={(e) => setPortalPassword(e.target.value)}
                placeholder="Enter new password to change"
                disabled={saving}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {errors.portal_password && <p className="text-sm text-destructive">{errors.portal_password}</p>}
            <p className="text-xs text-muted-foreground">
              Leave empty to keep your current password. This password is used for job portal accounts.
            </p>
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
