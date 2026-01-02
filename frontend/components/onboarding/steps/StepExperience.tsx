'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Briefcase, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  ExperienceEntry,
  ExperienceData,
  createEmptyExperience,
  getYearOptions,
  MONTH_OPTIONS,
} from '../types'

interface StepExperienceProps {
  initialData?: Partial<ExperienceData>
  onNext: (data: ExperienceData) => void
  onBack: () => void
  loading?: boolean
}

export function StepExperience({ initialData, onNext, onBack, loading }: StepExperienceProps) {
  const [entries, setEntries] = useState<ExperienceEntry[]>(
    initialData?.experience && initialData.experience.length > 0
      ? initialData.experience.map((exp) => ({
          ...exp,
          id: exp.id || crypto.randomUUID(),
        }))
      : [createEmptyExperience()]
  )
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    new Set(entries.length > 0 ? [entries[entries.length - 1].id] : [])
  )
  const [errors, setErrors] = useState<Record<string, Record<string, string>>>({})
  const yearOptions = getYearOptions()

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedIds)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedIds(newExpanded)
  }

  const updateEntry = (id: string, updates: Partial<ExperienceEntry>) => {
    setEntries(entries.map((entry) => (entry.id === id ? { ...entry, ...updates } : entry)))
    if (errors[id]) {
      const newErrors = { ...errors }
      Object.keys(updates).forEach((key) => {
        delete newErrors[id][key]
      })
      setErrors(newErrors)
    }
  }

  const addEntry = () => {
    const newEntry = createEmptyExperience()
    setEntries([...entries, newEntry])
    setExpandedIds(new Set([newEntry.id]))
  }

  const removeEntry = (id: string) => {
    if (entries.length > 1) {
      setEntries(entries.filter((entry) => entry.id !== id))
      const newErrors = { ...errors }
      delete newErrors[id]
      setErrors(newErrors)
      expandedIds.delete(id)
      setExpandedIds(new Set(expandedIds))
    }
  }

  const handleBulletsChange = (id: string, value: string) => {
    const bullets = value.split('\n').filter((line) => line.trim())
    updateEntry(id, { bullets })
  }

  const getBulletsText = (bullets: string[]) => {
    return bullets.join('\n')
  }

  const validateForm = () => {
    const newErrors: Record<string, Record<string, string>> = {}
    let isValid = true

    entries.forEach((entry) => {
      if (entry.company.trim() || entry.title.trim()) {
        const entryErrors: Record<string, string> = {}
        if (!entry.company.trim()) {
          entryErrors.company = 'Company name is required'
          isValid = false
        }
        if (!entry.title.trim()) {
          entryErrors.title = 'Job title is required'
          isValid = false
        }
        if (Object.keys(entryErrors).length > 0) {
          newErrors[entry.id] = entryErrors
        }
      }
    })

    setErrors(newErrors)
    return isValid
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      const filledEntries = entries.filter(
        (entry) => entry.company.trim() || entry.title.trim()
      )
      onNext({ experience: filledEntries })
    }
  }

  const getEntryTitle = (entry: ExperienceEntry) => {
    if (entry.title && entry.company) {
      return `${entry.title} at ${entry.company}`
    }
    if (entry.company) return entry.company
    if (entry.title) return entry.title
    return 'New Experience'
  }

  const getEntrySubtitle = (entry: ExperienceEntry) => {
    const parts = []
    if (entry.location) parts.push(entry.location)
    if (entry.start_date) {
      const endDate = entry.current ? 'Present' : entry.end_date || ''
      parts.push(`${entry.start_date} - ${endDate}`)
    }
    return parts.join(' | ')
  }

  const parseDate = (dateStr: string) => {
    if (!dateStr) return { month: '', year: '' }
    const [year, month] = dateStr.split('-')
    return { year: year || '', month: month || '' }
  }

  const formatDate = (month: string, year: string) => {
    if (!year) return ''
    if (!month) return year
    return `${year}-${month}`
  }

  return (
    <Card className="max-w-3xl mx-auto shadow-lg border-0 bg-card/80 backdrop-blur">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mb-4">
          <Briefcase className="h-7 w-7 text-primary" />
        </div>
        <CardTitle className="text-2xl">Work Experience</CardTitle>
        <CardDescription className="text-base">
          Add your work experience, internships, and relevant positions
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          <AnimatePresence mode="popLayout">
            {entries.map((entry) => {
              const isExpanded = expandedIds.has(entry.id)
              const hasData = entry.company || entry.title
              const startDate = parseDate(entry.start_date)
              const endDate = parseDate(entry.end_date)

              return (
                <motion.div
                  key={entry.id}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="border rounded-xl overflow-hidden bg-background shadow-sm">
                    <div
                      className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => toggleExpanded(entry.id)}
                    >
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium truncate">{getEntryTitle(entry)}</h3>
                        {hasData && !isExpanded && (
                          <p className="text-sm text-muted-foreground truncate">
                            {getEntrySubtitle(entry)}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        {entries.length > 1 && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation()
                              removeEntry(entry.id)
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                        {isExpanded ? (
                          <ChevronUp className="h-5 w-5 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-5 w-5 text-muted-foreground" />
                        )}
                      </div>
                    </div>

                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                        >
                          <div className="px-4 pb-4 space-y-4 border-t bg-muted/30">
                            <div className="pt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                              <div className="space-y-2">
                                <Label htmlFor={`company-${entry.id}`}>Company *</Label>
                                <Input
                                  id={`company-${entry.id}`}
                                  value={entry.company}
                                  onChange={(e) => updateEntry(entry.id, { company: e.target.value })}
                                  placeholder="e.g., Google"
                                  disabled={loading}
                                  className="bg-background"
                                />
                                {errors[entry.id]?.company && (
                                  <p className="text-sm text-destructive">{errors[entry.id].company}</p>
                                )}
                              </div>

                              <div className="space-y-2">
                                <Label htmlFor={`title-${entry.id}`}>Job Title *</Label>
                                <Input
                                  id={`title-${entry.id}`}
                                  value={entry.title}
                                  onChange={(e) => updateEntry(entry.id, { title: e.target.value })}
                                  placeholder="e.g., Software Engineer Intern"
                                  disabled={loading}
                                  className="bg-background"
                                />
                                {errors[entry.id]?.title && (
                                  <p className="text-sm text-destructive">{errors[entry.id].title}</p>
                                )}
                              </div>
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`location-${entry.id}`}>Location</Label>
                              <Input
                                id={`location-${entry.id}`}
                                value={entry.location}
                                onChange={(e) => updateEntry(entry.id, { location: e.target.value })}
                                placeholder="e.g., Mountain View, CA or Remote"
                                disabled={loading}
                                className="bg-background"
                              />
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              <div className="space-y-2">
                                <Label>Start Date</Label>
                                <div className="flex gap-2">
                                  <Select
                                    value={startDate.month}
                                    onValueChange={(month) =>
                                      updateEntry(entry.id, {
                                        start_date: formatDate(month, startDate.year),
                                      })
                                    }
                                    disabled={loading}
                                  >
                                    <SelectTrigger className="flex-1 bg-background">
                                      <SelectValue placeholder="Month" />
                                    </SelectTrigger>
                                    <SelectContent className="max-h-[280px]">
                                      {MONTH_OPTIONS.map((month) => (
                                        <SelectItem key={month.value} value={month.value}>
                                          {month.label}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                  <Select
                                    value={startDate.year}
                                    onValueChange={(year) =>
                                      updateEntry(entry.id, {
                                        start_date: formatDate(startDate.month, year),
                                      })
                                    }
                                    disabled={loading}
                                  >
                                    <SelectTrigger className="w-28 bg-background">
                                      <SelectValue placeholder="Year" />
                                    </SelectTrigger>
                                    <SelectContent className="max-h-[280px]">
                                      {yearOptions.map((year) => (
                                        <SelectItem key={year.value} value={year.value}>
                                          {year.label}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </div>
                              </div>

                              {!entry.current && (
                                <div className="space-y-2">
                                  <Label>End Date</Label>
                                  <div className="flex gap-2">
                                    <Select
                                      value={endDate.month}
                                      onValueChange={(month) =>
                                        updateEntry(entry.id, {
                                          end_date: formatDate(month, endDate.year),
                                        })
                                      }
                                      disabled={loading}
                                    >
                                      <SelectTrigger className="flex-1 bg-background">
                                        <SelectValue placeholder="Month" />
                                      </SelectTrigger>
                                      <SelectContent className="max-h-[280px]">
                                        {MONTH_OPTIONS.map((month) => (
                                          <SelectItem key={month.value} value={month.value}>
                                            {month.label}
                                          </SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                    <Select
                                      value={endDate.year}
                                      onValueChange={(year) =>
                                        updateEntry(entry.id, {
                                          end_date: formatDate(endDate.month, year),
                                        })
                                      }
                                      disabled={loading}
                                    >
                                      <SelectTrigger className="w-28 bg-background">
                                        <SelectValue placeholder="Year" />
                                      </SelectTrigger>
                                      <SelectContent className="max-h-[280px]">
                                        {yearOptions.map((year) => (
                                          <SelectItem key={year.value} value={year.value}>
                                            {year.label}
                                          </SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                  </div>
                                </div>
                              )}
                            </div>

                            <div className="flex items-center gap-3 pt-2">
                              <Switch
                                id={`current-${entry.id}`}
                                checked={entry.current}
                                onCheckedChange={(checked) => {
                                  if (checked) {
                                    // Uncheck all other entries first
                                    setEntries(entries.map((e) =>
                                      e.id === entry.id
                                        ? { ...e, current: true, end_date: '' }
                                        : { ...e, current: false }
                                    ))
                                  } else {
                                    updateEntry(entry.id, { current: false })
                                  }
                                }}
                                disabled={loading}
                              />
                              <Label htmlFor={`current-${entry.id}`} className="cursor-pointer text-sm">
                                I currently work here
                              </Label>
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`bullets-${entry.id}`}>
                                Key Accomplishments
                                <span className="text-muted-foreground text-xs ml-2">
                                  (One per line)
                                </span>
                              </Label>
                              <Textarea
                                id={`bullets-${entry.id}`}
                                value={getBulletsText(entry.bullets)}
                                onChange={(e) => handleBulletsChange(entry.id, e.target.value)}
                                placeholder={`Built microservices handling 1M+ requests/day
Improved API response time by 40%
Led a team of 5 engineers`}
                                rows={4}
                                disabled={loading}
                                className="font-mono text-sm bg-background"
                              />
                              <p className="text-xs text-muted-foreground">
                                Each line becomes a bullet point on your applications
                              </p>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </motion.div>
              )
            })}
          </AnimatePresence>

          <Button
            type="button"
            variant="outline"
            onClick={addEntry}
            disabled={loading}
            className="w-full border-dashed border-2 h-12 hover:border-primary hover:bg-primary/5 transition-colors"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Another Experience
          </Button>

          <p className="text-sm text-muted-foreground text-center">
            No work experience yet? No problem - you can skip this step
          </p>

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
