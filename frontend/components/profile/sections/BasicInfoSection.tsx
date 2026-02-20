'use client'

import { useState, useEffect, useRef } from 'react'
import { Pencil, User, MapPin, Shield, Linkedin, Github, Globe, Calendar } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  PersonalInfoData,
  SecurityClearance,
  SECURITY_CLEARANCE_OPTIONS,
  START_DATE_OPTIONS,
  PHONE_COUNTRY_CODES,
  US_STATES,
} from '@/components/onboarding/types'
import { Briefcase } from 'lucide-react'

interface AddressSuggestion {
  place_id: number
  display_name: string
  address: {
    house_number?: string
    road?: string
    city?: string
    town?: string
    village?: string
    state?: string
    postcode?: string
    country?: string
  }
}

interface BasicInfoSectionProps {
  profile: any
  userEmail: string
  isEditing: boolean
  onEdit: () => void
  onSave: (data: Record<string, any>) => Promise<void>
  onCancel: () => void
  saving: boolean
}

export function BasicInfoSection({
  profile,
  userEmail,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  saving,
}: BasicInfoSectionProps) {
  const [formData, setFormData] = useState<PersonalInfoData>({
    first_name: profile?.first_name || '',
    last_name: profile?.last_name || '',
    email: userEmail,
    phone: profile?.phone || '',
    phone_country_code: profile?.phone_country_code || 'us',
    linkedin_url: profile?.linkedin_url || '',
    github_url: profile?.github_url || '',
    portfolio_url: profile?.portfolio_url || '',
    address_line1: profile?.address_line1 || '',
    address_line2: profile?.address_line2 || '',
    city: profile?.city || '',
    state: profile?.state || '',
    zip_code: profile?.zip_code || '',
    country: profile?.country || 'United States',
    is_us_citizen: profile?.is_us_citizen ?? false,
    needs_visa_sponsorship: profile?.needs_visa_sponsorship ?? false,
    security_clearance: profile?.security_clearance || 'No Clearance',
    military_experience: profile?.military_experience ?? false,
    willing_to_relocate: profile?.willing_to_relocate ?? true,
    start_date: profile?.start_date || 'ASAP',
  })

  const [errors, setErrors] = useState<Partial<Record<keyof PersonalInfoData, string>>>({})
  const [addressQuery, setAddressQuery] = useState('')
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Reset form data when profile changes (after save + router.refresh)
  useEffect(() => {
    if (!isEditing) {
      setFormData({
        first_name: profile?.first_name || '',
        last_name: profile?.last_name || '',
        email: userEmail,
        phone: profile?.phone || '',
        phone_country_code: profile?.phone_country_code || 'us',
        linkedin_url: profile?.linkedin_url || '',
        github_url: profile?.github_url || '',
        portfolio_url: profile?.portfolio_url || '',
        address_line1: profile?.address_line1 || '',
        address_line2: profile?.address_line2 || '',
        city: profile?.city || '',
        state: profile?.state || '',
        zip_code: profile?.zip_code || '',
        country: profile?.country || 'United States',
        is_us_citizen: profile?.is_us_citizen ?? false,
        needs_visa_sponsorship: profile?.needs_visa_sponsorship ?? false,
        security_clearance: profile?.security_clearance || 'No Clearance',
        military_experience: profile?.military_experience ?? false,
        willing_to_relocate: profile?.willing_to_relocate ?? true,
        start_date: profile?.start_date || 'ASAP',
      })
      setErrors({})
    }
  }, [profile, isEditing, userEmail])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const fetchAddressSuggestions = async (query: string) => {
    if (query.length < 3) {
      setSuggestions([])
      return
    }

    setIsLoadingSuggestions(true)
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?` +
          new URLSearchParams({
            q: query,
            format: 'json',
            addressdetails: '1',
            countrycodes: 'us',
            limit: '5',
          }),
        { headers: { Accept: 'application/json' } }
      )

      if (response.ok) {
        const data = await response.json()
        setSuggestions(data)
        setShowSuggestions(true)
      }
    } catch (error) {
      console.error('Error fetching address suggestions:', error)
    } finally {
      setIsLoadingSuggestions(false)
    }
  }

  const handleAddressInputChange = (value: string) => {
    setAddressQuery(value)
    setFormData({ ...formData, address_line1: value })

    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    timeoutRef.current = setTimeout(() => fetchAddressSuggestions(value), 300)
  }

  const handleSuggestionSelect = (suggestion: AddressSuggestion) => {
    const addr = suggestion.address
    let street = ''
    if (addr.house_number) street += addr.house_number + ' '
    if (addr.road) street += addr.road

    setFormData({
      ...formData,
      address_line1: street.trim(),
      city: addr.city || addr.town || addr.village || '',
      state: addr.state || '',
      zip_code: addr.postcode || '',
      country: addr.country || 'United States',
    })
    setAddressQuery(street.trim())
    setShowSuggestions(false)
    setSuggestions([])
  }

  const validateForm = () => {
    const newErrors: Partial<Record<keyof PersonalInfoData, string>> = {}
    if (!formData.first_name.trim()) newErrors.first_name = 'First name is required'
    if (!formData.last_name.trim()) newErrors.last_name = 'Last name is required'
    if (formData.linkedin_url && !formData.linkedin_url.includes('linkedin.com')) {
      newErrors.linkedin_url = 'Please enter a valid LinkedIn URL'
    }
    if (formData.github_url && !formData.github_url.includes('github.com')) {
      newErrors.github_url = 'Please enter a valid GitHub URL'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateForm()) return

    const { email, ...dataToSave } = formData
    await onSave(dataToSave)
  }

  if (!isEditing) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>Your personal details</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onEdit}>
            <Pencil className="h-4 w-4 mr-1" />
            Edit
          </Button>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">First Name</p>
              <p className="font-medium">{profile?.first_name || 'Not set'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Last Name</p>
              <p className="font-medium">{profile?.last_name || 'Not set'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Email</p>
              <p className="font-medium">{userEmail}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Phone</p>
              <p className="font-medium">{profile?.phone || 'Not set'}</p>
            </div>
          </div>

          {(profile?.linkedin_url || profile?.github_url || profile?.portfolio_url) && (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground font-medium">Links</p>
              <div className="flex flex-wrap gap-3">
                {profile?.linkedin_url && (
                  <a href={profile.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline flex items-center gap-1">
                    <Linkedin className="h-3 w-3" /> LinkedIn
                  </a>
                )}
                {profile?.github_url && (
                  <a href={profile.github_url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline flex items-center gap-1">
                    <Github className="h-3 w-3" /> GitHub
                  </a>
                )}
                {profile?.portfolio_url && (
                  <a href={profile.portfolio_url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline flex items-center gap-1">
                    <Globe className="h-3 w-3" /> Portfolio
                  </a>
                )}
              </div>
            </div>
          )}

          {(profile?.city || profile?.state) && (
            <div>
              <p className="text-sm text-muted-foreground">Location</p>
              <p className="font-medium">
                {[profile?.city, profile?.state].filter(Boolean).join(', ')}
                {profile?.zip_code ? ` ${profile.zip_code}` : ''}
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">US Citizen</p>
              <p className="font-medium">{profile?.is_us_citizen ? 'Yes' : 'No'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Visa Sponsorship</p>
              <p className="font-medium">{profile?.needs_visa_sponsorship ? 'Required' : 'Not required'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Willing to Relocate</p>
              <p className="font-medium">{profile?.willing_to_relocate ? 'Yes' : 'No'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Start Date</p>
              <p className="font-medium">{profile?.start_date || 'Not set'}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Edit Basic Information</CardTitle>
        <CardDescription>Update your personal details</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Basic Info */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <User className="h-4 w-4 text-primary" />
              <h3 className="font-medium text-sm">Basic Information</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit_first_name">First Name *</Label>
                <Input
                  id="edit_first_name"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  disabled={saving}
                />
                {errors.first_name && <p className="text-sm text-destructive">{errors.first_name}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_last_name">Last Name *</Label>
                <Input
                  id="edit_last_name"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  disabled={saving}
                />
                {errors.last_name && <p className="text-sm text-destructive">{errors.last_name}</p>}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Email</Label>
              <Input value={userEmail} disabled className="bg-muted" />
              <p className="text-xs text-muted-foreground">Email cannot be changed</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit_phone">Phone Number</Label>
              <div className="flex gap-2">
                <Select
                  value={formData.phone_country_code}
                  onValueChange={(value) => setFormData({ ...formData, phone_country_code: value })}
                  disabled={saving}
                >
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PHONE_COUNTRY_CODES.map((code) => (
                      <SelectItem key={code.value} value={code.value}>{code.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  id="edit_phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="5551234567"
                  className="flex-1"
                  disabled={saving}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit_linkedin" className="flex items-center gap-2">
                  <Linkedin className="h-4 w-4" /> LinkedIn URL
                </Label>
                <Input
                  id="edit_linkedin"
                  type="url"
                  value={formData.linkedin_url}
                  onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })}
                  placeholder="https://linkedin.com/in/johndoe"
                  disabled={saving}
                />
                {errors.linkedin_url && <p className="text-sm text-destructive">{errors.linkedin_url}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_github" className="flex items-center gap-2">
                  <Github className="h-4 w-4" /> GitHub URL
                </Label>
                <Input
                  id="edit_github"
                  type="url"
                  value={formData.github_url}
                  onChange={(e) => setFormData({ ...formData, github_url: e.target.value })}
                  placeholder="https://github.com/johndoe"
                  disabled={saving}
                />
                {errors.github_url && <p className="text-sm text-destructive">{errors.github_url}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_portfolio" className="flex items-center gap-2">
                  <Globe className="h-4 w-4" /> Portfolio URL
                </Label>
                <Input
                  id="edit_portfolio"
                  type="url"
                  value={formData.portfolio_url}
                  onChange={(e) => setFormData({ ...formData, portfolio_url: e.target.value })}
                  placeholder="https://johndoe.dev"
                  disabled={saving}
                />
              </div>
            </div>
          </div>

          {/* Address */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <MapPin className="h-4 w-4 text-primary" />
              <h3 className="font-medium text-sm">Address</h3>
            </div>

            <div className="space-y-2 relative" ref={suggestionsRef}>
              <Label htmlFor="edit_address">Street Address</Label>
              <Input
                id="edit_address"
                value={addressQuery !== '' ? addressQuery : formData.address_line1}
                onChange={(e) => handleAddressInputChange(e.target.value)}
                onFocus={() => {
                  if (suggestions.length > 0) setShowSuggestions(true)
                  if (addressQuery === '' && formData.address_line1) setAddressQuery(formData.address_line1)
                }}
                placeholder="Start typing your address..."
                disabled={saving}
                autoComplete="off"
              />
              {showSuggestions && suggestions.length > 0 && (
                <div className="absolute z-50 w-full mt-1 bg-background border border-border rounded-lg shadow-lg max-h-60 overflow-auto">
                  {suggestions.map((suggestion) => (
                    <button
                      key={suggestion.place_id}
                      type="button"
                      onClick={() => handleSuggestionSelect(suggestion)}
                      className="w-full px-4 py-3 text-left hover:bg-muted border-b border-border last:border-b-0 transition-colors text-sm"
                    >
                      {suggestion.display_name}
                    </button>
                  ))}
                </div>
              )}
              {isLoadingSuggestions && (
                <p className="text-xs text-muted-foreground">Searching addresses...</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit_address2">Apartment, Suite, etc.</Label>
              <Input
                id="edit_address2"
                value={formData.address_line2}
                onChange={(e) => setFormData({ ...formData, address_line2: e.target.value })}
                placeholder="Apt 4B"
                disabled={saving}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit_city">City</Label>
                <Input
                  id="edit_city"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  disabled={saving}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_state">State</Label>
                <Select
                  value={formData.state}
                  onValueChange={(value) => setFormData({ ...formData, state: value })}
                  disabled={saving}
                >
                  <SelectTrigger id="edit_state">
                    <SelectValue placeholder="Select state" />
                  </SelectTrigger>
                  <SelectContent className="max-h-[280px]">
                    {US_STATES.map((state) => (
                      <SelectItem key={state} value={state}>{state}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit_zip">ZIP Code</Label>
                <Input
                  id="edit_zip"
                  value={formData.zip_code}
                  onChange={(e) => setFormData({ ...formData, zip_code: e.target.value })}
                  disabled={saving}
                />
              </div>
              <div className="space-y-2">
                <Label>Country</Label>
                <Select
                  value={formData.country}
                  onValueChange={(value) => setFormData({ ...formData, country: value })}
                  disabled={saving}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="United States">United States</SelectItem>
                    <SelectItem value="Canada">Canada</SelectItem>
                    <SelectItem value="United Kingdom">United Kingdom</SelectItem>
                    <SelectItem value="Other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Work Authorization */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <Shield className="h-4 w-4 text-primary" />
              <h3 className="font-medium text-sm">Work Authorization</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <Label>Are you a US Citizen?</Label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="edit_citizen" checked={formData.is_us_citizen === true}
                      onChange={() => setFormData({ ...formData, is_us_citizen: true })} disabled={saving} className="w-4 h-4 accent-primary" />
                    <span>Yes</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="edit_citizen" checked={formData.is_us_citizen === false}
                      onChange={() => setFormData({ ...formData, is_us_citizen: false })} disabled={saving} className="w-4 h-4 accent-primary" />
                    <span>No</span>
                  </label>
                </div>
              </div>
              <div className="space-y-3">
                <Label>Visa Sponsorship Required?</Label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="edit_visa" checked={formData.needs_visa_sponsorship === true}
                      onChange={() => setFormData({ ...formData, needs_visa_sponsorship: true })} disabled={saving} className="w-4 h-4 accent-primary" />
                    <span>Yes</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="edit_visa" checked={formData.needs_visa_sponsorship === false}
                      onChange={() => setFormData({ ...formData, needs_visa_sponsorship: false })} disabled={saving} className="w-4 h-4 accent-primary" />
                    <span>No</span>
                  </label>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Briefcase className="h-4 w-4" /> Security Clearance
              </Label>
              <Select
                value={formData.security_clearance}
                onValueChange={(value) => setFormData({ ...formData, security_clearance: value as SecurityClearance })}
                disabled={saving}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SECURITY_CLEARANCE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div>
                  <Label htmlFor="edit_military" className="cursor-pointer">Military Experience</Label>
                  <p className="text-sm text-muted-foreground">Do you have military experience?</p>
                </div>
                <Switch
                  id="edit_military"
                  checked={formData.military_experience}
                  onCheckedChange={(checked) => setFormData({ ...formData, military_experience: checked })}
                  disabled={saving}
                />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div>
                  <Label htmlFor="edit_relocate" className="cursor-pointer">Willing to Relocate</Label>
                  <p className="text-sm text-muted-foreground">Open to relocating for opportunities?</p>
                </div>
                <Switch
                  id="edit_relocate"
                  checked={formData.willing_to_relocate}
                  onCheckedChange={(checked) => setFormData({ ...formData, willing_to_relocate: checked })}
                  disabled={saving}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Calendar className="h-4 w-4" /> When can you start?
              </Label>
              <Select
                value={formData.start_date}
                onValueChange={(value) => setFormData({ ...formData, start_date: value })}
                disabled={saving}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {START_DATE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
