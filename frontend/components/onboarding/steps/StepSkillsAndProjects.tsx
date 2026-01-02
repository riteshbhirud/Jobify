'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Wrench, FolderGit2, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { TagInput } from '../shared/TagInput'
import {
  ProjectEntry,
  SkillsProjectsData,
  createEmptyProject,
} from '../types'

// Common skills for suggestions
const SKILL_SUGGESTIONS = [
  'JavaScript', 'TypeScript', 'Python', 'Java', 'C++', 'C#', 'Go', 'Rust', 'Ruby',
  'React', 'Vue.js', 'Angular', 'Next.js', 'Node.js', 'Express', 'Django', 'Flask',
  'PostgreSQL', 'MongoDB', 'MySQL', 'Redis', 'GraphQL', 'REST APIs',
  'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'CI/CD', 'Git',
  'Machine Learning', 'TensorFlow', 'PyTorch', 'Data Analysis', 'SQL',
  'HTML', 'CSS', 'Tailwind CSS', 'Sass', 'Figma',
  'Agile', 'Scrum', 'Technical Writing', 'Problem Solving',
]

interface StepSkillsAndProjectsProps {
  initialData?: Partial<SkillsProjectsData>
  onNext: (data: SkillsProjectsData) => void
  onBack: () => void
  loading?: boolean
}

export function StepSkillsAndProjects({
  initialData,
  onNext,
  onBack,
  loading,
}: StepSkillsAndProjectsProps) {
  const [skills, setSkills] = useState<string[]>(initialData?.skills || [])
  const [projects, setProjects] = useState<ProjectEntry[]>(
    initialData?.projects && initialData.projects.length > 0
      ? initialData.projects.map((p) => ({
          ...p,
          id: p.id || crypto.randomUUID(),
        }))
      : []
  )
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    new Set(projects.length > 0 ? [projects[projects.length - 1].id] : [])
  )
  const [errors, setErrors] = useState<Record<string, string>>({})

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedIds)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedIds(newExpanded)
  }

  const updateProject = (id: string, updates: Partial<ProjectEntry>) => {
    setProjects(projects.map((p) => (p.id === id ? { ...p, ...updates } : p)))
  }

  const addProject = () => {
    const newProject = createEmptyProject()
    setProjects([...projects, newProject])
    setExpandedIds(new Set([newProject.id]))
  }

  const removeProject = (id: string) => {
    setProjects(projects.filter((p) => p.id !== id))
    expandedIds.delete(id)
    setExpandedIds(new Set(expandedIds))
  }

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (skills.length === 0) {
      newErrors.skills = 'Add at least one skill'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      const filledProjects = projects.filter((p) => p.name.trim())
      onNext({ skills, projects: filledProjects })
    }
  }

  const getProjectTitle = (project: ProjectEntry) => {
    return project.name || 'New Project'
  }

  const getProjectSubtitle = (project: ProjectEntry) => {
    if (project.technologies.length > 0) {
      return project.technologies.slice(0, 3).join(', ') +
        (project.technologies.length > 3 ? ` +${project.technologies.length - 3} more` : '')
    }
    return project.description ? project.description.slice(0, 50) + '...' : ''
  }

  return (
    <Card className="max-w-3xl mx-auto shadow-lg border-0 bg-card/80 backdrop-blur">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mb-4">
          <Wrench className="h-7 w-7 text-primary" />
        </div>
        <CardTitle className="text-2xl">Skills & Projects</CardTitle>
        <CardDescription className="text-base">
          Highlight your technical skills and showcase your best projects
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Skills Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <Wrench className="h-4 w-4 text-primary" />
              <h3 className="font-medium">Skills</h3>
            </div>

            <TagInput
              tags={skills}
              onTagsChange={setSkills}
              placeholder="Add a skill (e.g., React, Python, AWS)"
              disabled={loading}
              suggestions={SKILL_SUGGESTIONS}
            />
            {errors.skills && (
              <p className="text-sm text-destructive">{errors.skills}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Tip: Add both technical skills (programming languages, frameworks) and soft skills
            </p>
          </div>

          {/* Projects Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <FolderGit2 className="h-4 w-4 text-primary" />
              <h3 className="font-medium">Projects (Optional)</h3>
            </div>

            <AnimatePresence mode="popLayout">
              {projects.map((project) => {
                const isExpanded = expandedIds.has(project.id)
                const hasData = project.name

                return (
                  <motion.div
                    key={project.id}
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10, height: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="border rounded-xl overflow-hidden bg-background shadow-sm">
                      <div
                        className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                        onClick={() => toggleExpanded(project.id)}
                      >
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium truncate">{getProjectTitle(project)}</h3>
                          {hasData && !isExpanded && (
                            <p className="text-sm text-muted-foreground truncate">
                              {getProjectSubtitle(project)}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2 ml-4">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation()
                              removeProject(project.id)
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
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
                                <Label htmlFor={`name-${project.id}`}>Project Name</Label>
                                <Input
                                  id={`name-${project.id}`}
                                  value={project.name}
                                  onChange={(e) => updateProject(project.id, { name: e.target.value })}
                                  placeholder="e.g., TaskFlow"
                                  disabled={loading}
                                  className="bg-background"
                                />
                              </div>

                              <div className="space-y-2">
                                <Label htmlFor={`description-${project.id}`}>Description</Label>
                                <Textarea
                                  id={`description-${project.id}`}
                                  value={project.description}
                                  onChange={(e) => updateProject(project.id, { description: e.target.value })}
                                  placeholder="A brief description of what this project does and your role"
                                  rows={3}
                                  disabled={loading}
                                  className="bg-background"
                                />
                              </div>

                              <div className="space-y-2">
                                <Label htmlFor={`url-${project.id}`}>Project URL (Optional)</Label>
                                <Input
                                  id={`url-${project.id}`}
                                  type="url"
                                  value={project.url}
                                  onChange={(e) => updateProject(project.id, { url: e.target.value })}
                                  placeholder="https://github.com/username/project"
                                  disabled={loading}
                                  className="bg-background"
                                />
                              </div>

                              <div className="space-y-2">
                                <Label>Technologies Used</Label>
                                <TagInput
                                  tags={project.technologies}
                                  onTagsChange={(technologies) =>
                                    updateProject(project.id, { technologies })
                                  }
                                  placeholder="Add technology (e.g., React, Node.js)"
                                  disabled={loading}
                                  suggestions={SKILL_SUGGESTIONS}
                                />
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
              onClick={addProject}
              disabled={loading}
              className="w-full border-dashed border-2 h-12 hover:border-primary hover:bg-primary/5 transition-colors"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add a Project
            </Button>

            {projects.length === 0 && (
              <p className="text-sm text-muted-foreground text-center">
                Projects help showcase your practical experience. Add any personal, academic,
                or open-source projects you've worked on.
              </p>
            )}
          </div>

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
