'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, GraduationCap, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  EducationEntry,
  EducationData,
  DEGREE_OPTIONS,
  createEmptyEducation,
  getYearOptions,
} from '../types'

interface StepEducationProps {
  initialData?: Partial<EducationData>
  onNext: (data: EducationData) => void
  onBack: () => void
  loading?: boolean
}

export function StepEducation({ initialData, onNext, onBack, loading }: StepEducationProps) {
  const [entries, setEntries] = useState<EducationEntry[]>(
    initialData?.education && initialData.education.length > 0
      ? initialData.education
      : [createEmptyEducation()]
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

  const updateEntry = (id: string, updates: Partial<EducationEntry>) => {
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
    const newEntry = createEmptyEducation()
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

  const validateForm = () => {
    const newErrors: Record<string, Record<string, string>> = {}
    let isValid = true

    entries.forEach((entry) => {
      if (entry.school.trim() || entry.degree) {
        const entryErrors: Record<string, string> = {}
        if (!entry.school.trim()) {
          entryErrors.school = 'School name is required'
          isValid = false
        }
        if (!entry.degree) {
          entryErrors.degree = 'Degree is required'
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
      const filledEntries = entries.filter((entry) => entry.school.trim() || entry.degree)
      onNext({ education: filledEntries })
    }
  }

  const getEntryTitle = (entry: EducationEntry) => {
    if (entry.school) return entry.school
    return 'New Education'
  }

  const getEntrySubtitle = (entry: EducationEntry) => {
    const parts = []
    if (entry.degree) parts.push(entry.degree)
    if (entry.discipline) parts.push(entry.discipline)
    return parts.join(' in ')
  }

  return (
    <Card className="max-w-3xl mx-auto shadow-lg border-0 bg-card/80 backdrop-blur">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mb-4">
          <GraduationCap className="h-7 w-7 text-primary" />
        </div>
        <CardTitle className="text-2xl">Education</CardTitle>
        <CardDescription className="text-base">
          Add your educational background
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          <AnimatePresence mode="popLayout">
            {entries.map((entry) => {
              const isExpanded = expandedIds.has(entry.id)
              const hasData = entry.school || entry.degree

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
                            <div className="pt-4 space-y-2">
                              <Label htmlFor={`school-${entry.id}`}>School / University *</Label>
                              <Input
                                id={`school-${entry.id}`}
                                value={entry.school}
                                onChange={(e) => updateEntry(entry.id, { school: e.target.value })}
                                placeholder="e.g., Stanford University"
                                disabled={loading}
                                className="bg-background"
                              />
                              {errors[entry.id]?.school && (
                                <p className="text-sm text-destructive">{errors[entry.id].school}</p>
                              )}
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              <div className="space-y-2">
                                <Label htmlFor={`degree-${entry.id}`}>Degree *</Label>
                                <Select
                                  value={entry.degree}
                                  onValueChange={(value) => updateEntry(entry.id, { degree: value })}
                                  disabled={loading}
                                >
                                  <SelectTrigger id={`degree-${entry.id}`} className="bg-background">
                                    <SelectValue placeholder="Select degree" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {DEGREE_OPTIONS.map((option) => (
                                      <SelectItem key={option.value} value={option.value}>
                                        {option.label}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                                {errors[entry.id]?.degree && (
                                  <p className="text-sm text-destructive">{errors[entry.id].degree}</p>
                                )}
                              </div>

                              <div className="space-y-2">
                                <Label htmlFor={`discipline-${entry.id}`}>Field of Study</Label>
                                <Input
                                  id={`discipline-${entry.id}`}
                                  value={entry.discipline}
                                  onChange={(e) => updateEntry(entry.id, { discipline: e.target.value })}
                                  placeholder="e.g., Computer Science"
                                  disabled={loading}
                                  className="bg-background"
                                />
                              </div>
                            </div>

                            <div className="grid grid-cols-3 gap-4">
                              <div className="space-y-2">
                                <Label htmlFor={`gpa-${entry.id}`}>GPA</Label>
                                <Input
                                  id={`gpa-${entry.id}`}
                                  value={entry.gpa}
                                  onChange={(e) => updateEntry(entry.id, { gpa: e.target.value })}
                                  placeholder="3.8"
                                  disabled={loading}
                                  className="bg-background"
                                />
                              </div>

                              <div className="space-y-2">
                                <Label htmlFor={`start_year-${entry.id}`}>Start Year</Label>
                                <Select
                                  value={entry.start_year}
                                  onValueChange={(value) => updateEntry(entry.id, { start_year: value })}
                                  disabled={loading}
                                >
                                  <SelectTrigger id={`start_year-${entry.id}`} className="bg-background">
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

                              <div className="space-y-2">
                                <Label htmlFor={`end_year-${entry.id}`}>
                                  {entry.current ? 'Expected' : 'End Year'}
                                </Label>
                                <Select
                                  value={entry.end_year}
                                  onValueChange={(value) => updateEntry(entry.id, { end_year: value })}
                                  disabled={loading}
                                >
                                  <SelectTrigger id={`end_year-${entry.id}`} className="bg-background">
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

                            <div className="flex items-center gap-3 pt-2">
                              <Switch
                                id={`current-${entry.id}`}
                                checked={entry.current}
                                onCheckedChange={(checked) => {
                                  if (checked) {
                                    // Uncheck all other entries first
                                    setEntries(entries.map((e) =>
                                      e.id === entry.id
                                        ? { ...e, current: true }
                                        : { ...e, current: false }
                                    ))
                                  } else {
                                    updateEntry(entry.id, { current: false })
                                  }
                                }}
                                disabled={loading}
                              />
                              <Label htmlFor={`current-${entry.id}`} className="cursor-pointer text-sm">
                                I am currently studying here
                              </Label>
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
            Add Another Education
          </Button>

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
