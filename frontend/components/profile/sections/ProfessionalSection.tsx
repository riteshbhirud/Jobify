'use client'

import { useState } from 'react'
import { Pencil, GraduationCap, Briefcase, Wrench, FolderGit2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { StepEducation } from '@/components/onboarding/steps/StepEducation'
import { StepExperience } from '@/components/onboarding/steps/StepExperience'
import { StepSkillsAndProjects } from '@/components/onboarding/steps/StepSkillsAndProjects'
import type { EducationData, ExperienceData, SkillsProjectsData } from '@/components/onboarding/types'

interface ProfessionalSectionProps {
  profile: any
  onSave: (data: Record<string, any>) => Promise<void>
  saving: boolean
}

type DialogType = 'education' | 'experience' | 'skills' | null

export function ProfessionalSection({ profile, onSave, saving }: ProfessionalSectionProps) {
  const [openDialog, setOpenDialog] = useState<DialogType>(null)

  const handleEducationSave = async (data: EducationData) => {
    await onSave(data)
    setOpenDialog(null)
  }

  const handleExperienceSave = async (data: ExperienceData) => {
    await onSave(data)
    setOpenDialog(null)
  }

  const handleSkillsSave = async (data: SkillsProjectsData) => {
    await onSave(data)
    setOpenDialog(null)
  }

  const education = profile?.education || []
  const experience = profile?.experience || []
  const skills = profile?.skills || []
  const projects = profile?.projects || []

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Professional Background</CardTitle>
          <CardDescription>Your education, experience, skills, and projects</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Education */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-medium flex items-center gap-2 text-sm">
                <GraduationCap className="h-4 w-4 text-primary" />
                Education
              </h3>
              <Button variant="ghost" size="sm" onClick={() => setOpenDialog('education')}>
                <Pencil className="h-3 w-3 mr-1" />
                Edit
              </Button>
            </div>
            {education.length > 0 ? (
              <div className="space-y-2">
                {education.map((edu: any, i: number) => (
                  <div key={i} className="p-3 rounded-lg bg-muted/50">
                    <p className="font-medium text-sm">{edu.school}</p>
                    <p className="text-sm text-muted-foreground">
                      {[edu.degree, edu.discipline].filter(Boolean).join(' in ')}
                      {edu.gpa ? ` (GPA: ${edu.gpa})` : ''}
                    </p>
                    {(edu.start_year || edu.end_year) && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {edu.start_year}{edu.start_year && edu.end_year ? ' - ' : ''}{edu.current ? 'Present' : edu.end_year}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No education added</p>
            )}
          </div>

          <div className="border-t" />

          {/* Experience */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-medium flex items-center gap-2 text-sm">
                <Briefcase className="h-4 w-4 text-primary" />
                Work Experience
              </h3>
              <Button variant="ghost" size="sm" onClick={() => setOpenDialog('experience')}>
                <Pencil className="h-3 w-3 mr-1" />
                Edit
              </Button>
            </div>
            {experience.length > 0 ? (
              <div className="space-y-2">
                {experience.map((exp: any, i: number) => (
                  <div key={i} className="p-3 rounded-lg bg-muted/50">
                    <p className="font-medium text-sm">
                      {exp.title}{exp.title && exp.company ? ' at ' : ''}{exp.company}
                    </p>
                    {exp.location && (
                      <p className="text-sm text-muted-foreground">{exp.location}</p>
                    )}
                    {(exp.start_date || exp.end_date) && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {exp.start_date}{exp.start_date && (exp.end_date || exp.current) ? ' - ' : ''}{exp.current ? 'Present' : exp.end_date}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No experience added</p>
            )}
          </div>

          <div className="border-t" />

          {/* Skills & Projects */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-medium flex items-center gap-2 text-sm">
                <Wrench className="h-4 w-4 text-primary" />
                Skills & Projects
              </h3>
              <Button variant="ghost" size="sm" onClick={() => setOpenDialog('skills')}>
                <Pencil className="h-3 w-3 mr-1" />
                Edit
              </Button>
            </div>

            {skills.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground font-medium">Skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {skills.map((skill: string) => (
                    <Badge key={skill} variant="secondary" className="text-xs">{skill}</Badge>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No skills added</p>
            )}

            {projects.length > 0 && (
              <div className="space-y-2 mt-3">
                <p className="text-xs text-muted-foreground font-medium flex items-center gap-1">
                  <FolderGit2 className="h-3 w-3" /> Projects
                </p>
                {projects.map((proj: any, i: number) => (
                  <div key={i} className="p-3 rounded-lg bg-muted/50">
                    <p className="font-medium text-sm">{proj.name}</p>
                    {proj.description && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{proj.description}</p>
                    )}
                    {proj.technologies?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {proj.technologies.map((tech: string) => (
                          <Badge key={tech} variant="outline" className="text-xs">{tech}</Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Education Dialog */}
      <Dialog open={openDialog === 'education'} onOpenChange={(open) => !open && setOpenDialog(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Education</DialogTitle>
            <DialogDescription>Update your educational background</DialogDescription>
          </DialogHeader>
          <StepEducation
            initialData={{ education }}
            onNext={() => {}}
            onBack={() => setOpenDialog(null)}
            loading={saving}
            mode="edit"
            onSave={handleEducationSave}
          />
        </DialogContent>
      </Dialog>

      {/* Experience Dialog */}
      <Dialog open={openDialog === 'experience'} onOpenChange={(open) => !open && setOpenDialog(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Work Experience</DialogTitle>
            <DialogDescription>Update your work experience</DialogDescription>
          </DialogHeader>
          <StepExperience
            initialData={{ experience }}
            onNext={() => {}}
            onBack={() => setOpenDialog(null)}
            loading={saving}
            mode="edit"
            onSave={handleExperienceSave}
          />
        </DialogContent>
      </Dialog>

      {/* Skills & Projects Dialog */}
      <Dialog open={openDialog === 'skills'} onOpenChange={(open) => !open && setOpenDialog(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Skills & Projects</DialogTitle>
            <DialogDescription>Update your skills and project portfolio</DialogDescription>
          </DialogHeader>
          <StepSkillsAndProjects
            initialData={{ skills, projects }}
            onNext={() => {}}
            onBack={() => setOpenDialog(null)}
            loading={saving}
            mode="edit"
            onSave={handleSkillsSave}
          />
        </DialogContent>
      </Dialog>
    </>
  )
}
