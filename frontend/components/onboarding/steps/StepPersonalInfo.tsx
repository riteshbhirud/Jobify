'use client'

import { useState, useEffect, useRef } from 'react'
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
} from '../types'
import { User, MapPin, Briefcase, Linkedin, Github, Globe, Shield, Calendar } from 'lucide-react'

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

interface StepPersonalInfoProps {
  initialData?: Partial<PersonalInfoData>
  onNext: (data: PersonalInfoData) => void
  loading?: boolean
  userEmail?: string
}

export function StepPersonalInfo({ initialData, onNext, loading, userEmail }: StepPersonalInfoProps) {
  const [formData, setFormData] = useState<PersonalInfoData>({
    first_name: initialData?.first_name || '',
    last_name: initialData?.last_name || '',
    email: userEmail || initialData?.email || '',
    phone: initialData?.phone || '',
    phone_country_code: initialData?.phone_country_code || 'us',
    linkedin_url: initialData?.linkedin_url || '',
    github_url: initialData?.github_url || '',
    portfolio_url: initialData?.portfolio_url || '',
    address_line1: initialData?.address_line1 || '',
    address_line2: initialData?.address_line2 || '',
    city: initialData?.city || '',
    state: initialData?.state || '',
    zip_code: initialData?.zip_code || '',
    country: initialData?.country || 'United States',
    is_us_citizen: initialData?.is_us_citizen ?? false,
    needs_visa_sponsorship: initialData?.needs_visa_sponsorship ?? false,
    security_clearance: initialData?.security_clearance || 'No Clearance',
    military_experience: initialData?.military_experience ?? false,
    willing_to_relocate: initialData?.willing_to_relocate ?? true,
    start_date: initialData?.start_date || 'ASAP',
  })

  const [errors, setErrors] = useState<Partial<Record<keyof PersonalInfoData, string>>>({})
  const [addressQuery, setAddressQuery] = useState('')
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

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

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    timeoutRef.current = setTimeout(() => {
      fetchAddressSuggestions(value)
    }, 300)
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

    if (!formData.first_name.trim()) {
      newErrors.first_name = 'First name is required'
    }
    if (!formData.last_name.trim()) {
      newErrors.last_name = 'Last name is required'
    }
    if (!formData.city.trim()) {
      newErrors.city = 'City is required'
    }
    if (!formData.state) {
      newErrors.state = 'State is required'
    }
    if (!formData.zip_code.trim()) {
      newErrors.zip_code = 'ZIP code is required'
    }
    if (formData.linkedin_url && !formData.linkedin_url.includes('linkedin.com')) {
      newErrors.linkedin_url = 'Please enter a valid LinkedIn URL'
    }
    if (formData.github_url && !formData.github_url.includes('github.com')) {
      newErrors.github_url = 'Please enter a valid GitHub URL'
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
          <User className="h-7 w-7 text-primary" />
        </div>
        <CardTitle className="text-2xl">Let's get to know you</CardTitle>
        <CardDescription className="text-base">
          This information will be used on your job applications
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Basic Info Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <User className="h-4 w-4 text-primary" />
              <h3 className="font-medium">Basic Information</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name *</Label>
                <Input
                  id="first_name"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  placeholder="John"
                  disabled={loading}
                  className="bg-background"
                />
                {errors.first_name && <p className="text-sm text-destructive">{errors.first_name}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name *</Label>
                <Input
                  id="last_name"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  placeholder="Doe"
                  disabled={loading}
                  className="bg-background"
                />
                {errors.last_name && <p className="text-sm text-destructive">{errors.last_name}</p>}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                disabled
                className="bg-muted"
              />
              <p className="text-xs text-muted-foreground">Email cannot be changed</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Phone Number</Label>
              <div className="flex gap-2">
                <Select
                  value={formData.phone_country_code}
                  onValueChange={(value) => setFormData({ ...formData, phone_country_code: value })}
                  disabled={loading}
                >
                  <SelectTrigger className="w-32 bg-background">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PHONE_COUNTRY_CODES.map((code) => (
                      <SelectItem key={code.value} value={code.value}>
                        {code.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  id="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="5551234567"
                  className="flex-1 bg-background"
                  disabled={loading}
                />
              </div>
            </div>

            {/* Social Links */}
            <div className="grid grid-cols-1 gap-4">
              <div className="space-y-2">
                <Label htmlFor="linkedin_url" className="flex items-center gap-2">
                  <Linkedin className="h-4 w-4" /> LinkedIn URL
                </Label>
                <Input
                  id="linkedin_url"
                  type="url"
                  value={formData.linkedin_url}
                  onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })}
                  placeholder="https://linkedin.com/in/johndoe"
                  disabled={loading}
                  className="bg-background"
                />
                {errors.linkedin_url && <p className="text-sm text-destructive">{errors.linkedin_url}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="github_url" className="flex items-center gap-2">
                  <Github className="h-4 w-4" /> GitHub URL (Optional)
                </Label>
                <Input
                  id="github_url"
                  type="url"
                  value={formData.github_url}
                  onChange={(e) => setFormData({ ...formData, github_url: e.target.value })}
                  placeholder="https://github.com/johndoe"
                  disabled={loading}
                  className="bg-background"
                />
                {errors.github_url && <p className="text-sm text-destructive">{errors.github_url}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="portfolio_url" className="flex items-center gap-2">
                  <Globe className="h-4 w-4" /> Portfolio URL (Optional)
                </Label>
                <Input
                  id="portfolio_url"
                  type="url"
                  value={formData.portfolio_url}
                  onChange={(e) => setFormData({ ...formData, portfolio_url: e.target.value })}
                  placeholder="https://johndoe.dev"
                  disabled={loading}
                  className="bg-background"
                />
              </div>
            </div>
          </div>

          {/* Address Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <MapPin className="h-4 w-4 text-primary" />
              <h3 className="font-medium">Address</h3>
            </div>

            <div className="space-y-2 relative" ref={suggestionsRef}>
              <Label htmlFor="address_search">Street Address</Label>
              <Input
                id="address_search"
                value={addressQuery !== '' ? addressQuery : formData.address_line1}
                onChange={(e) => handleAddressInputChange(e.target.value)}
                onFocus={() => {
                  if (suggestions.length > 0) setShowSuggestions(true)
                  if (addressQuery === '' && formData.address_line1) {
                    setAddressQuery(formData.address_line1)
                  }
                }}
                placeholder="Start typing your address..."
                disabled={loading}
                autoComplete="off"
                className="bg-background"
              />

              {showSuggestions && suggestions.length > 0 && (
                <div className="absolute z-50 w-full mt-1 bg-background border border-border rounded-xl shadow-lg max-h-60 overflow-auto">
                  {suggestions.map((suggestion) => (
                    <button
                      key={suggestion.place_id}
                      type="button"
                      onClick={() => handleSuggestionSelect(suggestion)}
                      className="w-full px-4 py-3 text-left hover:bg-muted border-b border-border last:border-b-0 transition-colors first:rounded-t-xl last:rounded-b-xl"
                    >
                      <div className="text-sm">{suggestion.display_name}</div>
                    </button>
                  ))}
                </div>
              )}

              {isLoadingSuggestions && (
                <p className="text-xs text-muted-foreground mt-1">Searching addresses...</p>
              )}
              <p className="text-xs text-muted-foreground">
                Start typing to see suggestions
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="address_line2">Apartment, Suite, etc. (Optional)</Label>
              <Input
                id="address_line2"
                value={formData.address_line2}
                onChange={(e) => setFormData({ ...formData, address_line2: e.target.value })}
                placeholder="Apt 4B"
                disabled={loading}
                className="bg-background"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="city">City *</Label>
                <Input
                  id="city"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="San Francisco"
                  disabled={loading}
                  className="bg-background"
                />
                {errors.city && <p className="text-sm text-destructive">{errors.city}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="state">State *</Label>
                <Select
                  value={formData.state}
                  onValueChange={(value) => setFormData({ ...formData, state: value })}
                  disabled={loading}
                >
                  <SelectTrigger id="state" className="bg-background">
                    <SelectValue placeholder="Select state" />
                  </SelectTrigger>
                  <SelectContent className="max-h-[280px]">
                    {US_STATES.map((state) => (
                      <SelectItem key={state} value={state}>
                        {state}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.state && <p className="text-sm text-destructive">{errors.state}</p>}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="zip_code">ZIP Code *</Label>
                <Input
                  id="zip_code"
                  value={formData.zip_code}
                  onChange={(e) => setFormData({ ...formData, zip_code: e.target.value })}
                  placeholder="94102"
                  disabled={loading}
                  className="bg-background"
                />
                {errors.zip_code && <p className="text-sm text-destructive">{errors.zip_code}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="country">Country</Label>
                <Select
                  value={formData.country}
                  onValueChange={(value) => setFormData({ ...formData, country: value })}
                  disabled={loading}
                >
                  <SelectTrigger id="country" className="bg-background">
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

          {/* Work Authorization Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <Shield className="h-4 w-4 text-primary" />
              <h3 className="font-medium">Work Authorization</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <Label>Are you a US Citizen?</Label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="is_us_citizen"
                      checked={formData.is_us_citizen === true}
                      onChange={() => setFormData({ ...formData, is_us_citizen: true })}
                      disabled={loading}
                      className="w-4 h-4 accent-primary"
                    />
                    <span>Yes</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="is_us_citizen"
                      checked={formData.is_us_citizen === false}
                      onChange={() => setFormData({ ...formData, is_us_citizen: false })}
                      disabled={loading}
                      className="w-4 h-4 accent-primary"
                    />
                    <span>No</span>
                  </label>
                </div>
              </div>

              <div className="space-y-3">
                <Label>Will you require visa sponsorship?</Label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="needs_visa_sponsorship"
                      checked={formData.needs_visa_sponsorship === true}
                      onChange={() => setFormData({ ...formData, needs_visa_sponsorship: true })}
                      disabled={loading}
                      className="w-4 h-4 accent-primary"
                    />
                    <span>Yes</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="needs_visa_sponsorship"
                      checked={formData.needs_visa_sponsorship === false}
                      onChange={() => setFormData({ ...formData, needs_visa_sponsorship: false })}
                      disabled={loading}
                      className="w-4 h-4 accent-primary"
                    />
                    <span>No</span>
                  </label>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="security_clearance" className="flex items-center gap-2">
                <Briefcase className="h-4 w-4" />
                Security Clearance
              </Label>
              <Select
                value={formData.security_clearance}
                onValueChange={(value) => setFormData({ ...formData, security_clearance: value as SecurityClearance })}
                disabled={loading}
              >
                <SelectTrigger id="security_clearance" className="bg-background">
                  <SelectValue placeholder="Select clearance level" />
                </SelectTrigger>
                <SelectContent>
                  {SECURITY_CLEARANCE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-4 pt-2">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div>
                  <Label htmlFor="military_experience" className="cursor-pointer">Military Experience</Label>
                  <p className="text-sm text-muted-foreground">Do you have military experience?</p>
                </div>
                <Switch
                  id="military_experience"
                  checked={formData.military_experience}
                  onCheckedChange={(checked) => setFormData({ ...formData, military_experience: checked })}
                  disabled={loading}
                />
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div>
                  <Label htmlFor="willing_to_relocate" className="cursor-pointer">Willing to Relocate</Label>
                  <p className="text-sm text-muted-foreground">Open to relocating for opportunities?</p>
                </div>
                <Switch
                  id="willing_to_relocate"
                  checked={formData.willing_to_relocate}
                  onCheckedChange={(checked) => setFormData({ ...formData, willing_to_relocate: checked })}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="start_date" className="flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                When can you start?
              </Label>
              <Select
                value={formData.start_date}
                onValueChange={(value) => setFormData({ ...formData, start_date: value })}
                disabled={loading}
              >
                <SelectTrigger id="start_date" className="bg-background">
                  <SelectValue placeholder="Select availability" />
                </SelectTrigger>
                <SelectContent>
                  {START_DATE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex justify-end pt-6">
            <Button type="submit" disabled={loading} className="px-8">
              {loading ? 'Saving...' : 'Continue'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
