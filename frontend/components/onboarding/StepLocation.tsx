'use client'

import { useState, useEffect, useRef } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

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
    country_code?: string
  }
}

interface LocationData {
  address_line1: string
  address_line2: string
  city: string
  state: string
  zip_code: string
  country: string
}

interface StepLocationProps {
  initialData?: Partial<LocationData>
  onNext: (data: LocationData) => void
  onBack: () => void
  loading?: boolean
}

const US_STATES = [
  "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
  "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
  "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
  "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
  "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
  "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
  "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
  "Wisconsin", "Wyoming"
]

export function StepLocation({ initialData, onNext, onBack, loading }: StepLocationProps) {
  const [formData, setFormData] = useState<LocationData>({
    address_line1: initialData?.address_line1 || '',
    address_line2: initialData?.address_line2 || '',
    city: initialData?.city || '',
    state: initialData?.state || '',
    zip_code: initialData?.zip_code || '',
    country: initialData?.country || 'United States',
  })

  const [errors, setErrors] = useState<Partial<Record<keyof LocationData, string>>>({})
  const [addressQuery, setAddressQuery] = useState('')
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Close suggestions when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Fetch address suggestions from Nominatim
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
          countrycodes: 'us', // Focus on US addresses
          limit: '5'
        }),
        {
          headers: {
            'Accept': 'application/json',
          }
        }
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

  // Debounce address search
  const handleAddressInputChange = (value: string) => {
    setAddressQuery(value)
    // Also update formData so the value doesn't revert
    setFormData({ ...formData, address_line1: value })

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    timeoutRef.current = setTimeout(() => {
      fetchAddressSuggestions(value)
    }, 300) // Wait 300ms after user stops typing
  }

  // Handle suggestion selection
  const handleSuggestionSelect = (suggestion: AddressSuggestion) => {
    const addr = suggestion.address

    // Build street address
    let street = ''
    if (addr.house_number) street += addr.house_number + ' '
    if (addr.road) street += addr.road

    const streetAddress = street.trim() || ''

    setFormData({
      ...formData,
      address_line1: streetAddress,
      city: addr.city || addr.town || addr.village || '',
      state: addr.state || '',
      zip_code: addr.postcode || '',
      country: addr.country || 'United States',
    })

    setAddressQuery(streetAddress)
    setShowSuggestions(false)
    setSuggestions([])
  }

  const validateForm = () => {
    const newErrors: Partial<Record<keyof LocationData, string>> = {}

    if (!formData.city.trim()) {
      newErrors.city = "City is required"
    }
    if (!formData.state) {
      newErrors.state = "State is required"
    }
    if (!formData.zip_code.trim()) {
      newErrors.zip_code = "ZIP code is required"
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
        <CardTitle>Where are you located?</CardTitle>
        <CardDescription>
          This helps us find jobs near you and fill out applications accurately
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2 relative" ref={suggestionsRef}>
            <Label htmlFor="address_search">Street Address</Label>
            <Input
              id="address_search"
              value={addressQuery !== '' ? addressQuery : formData.address_line1}
              onChange={(e) => handleAddressInputChange(e.target.value)}
              onFocus={() => {
                if (suggestions.length > 0) setShowSuggestions(true)
                // Sync addressQuery with current value when focusing
                if (addressQuery === '' && formData.address_line1) {
                  setAddressQuery(formData.address_line1)
                }
              }}
              placeholder="Start typing your address..."
              disabled={loading}
              autoComplete="off"
            />

            {/* Address Suggestions Dropdown */}
            {showSuggestions && suggestions.length > 0 && (
              <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-auto">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion.place_id}
                    type="button"
                    onClick={() => handleSuggestionSelect(suggestion)}
                    className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors"
                  >
                    <div className="text-sm font-medium text-gray-900">
                      {suggestion.display_name}
                    </div>
                  </button>
                ))}
              </div>
            )}

            {isLoadingSuggestions && (
              <p className="text-xs text-muted-foreground mt-1">
                Searching addresses...
              </p>
            )}

            <p className="text-xs text-muted-foreground mt-1">
              Start typing to see suggestions. We'll auto-fill the rest!
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
              />
              {errors.city && (
                <p className="text-sm text-destructive">{errors.city}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="state">State *</Label>
              <Select
                value={formData.state}
                onValueChange={(value) => setFormData({ ...formData, state: value })}
                disabled={loading}
              >
                <SelectTrigger id="state">
                  <SelectValue placeholder="Select state" />
                </SelectTrigger>
                <SelectContent>
                  {US_STATES.map((state) => (
                    <SelectItem key={state} value={state}>
                      {state}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.state && (
                <p className="text-sm text-destructive">{errors.state}</p>
              )}
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
              />
              {errors.zip_code && (
                <p className="text-sm text-destructive">{errors.zip_code}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="country">Country</Label>
              <Select
                value={formData.country}
                onValueChange={(value) => setFormData({ ...formData, country: value })}
                disabled={loading}
              >
                <SelectTrigger id="country">
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
