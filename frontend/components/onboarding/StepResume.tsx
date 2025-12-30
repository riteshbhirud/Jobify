'use client'

import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"

interface ResumeData {
  resume_url: string
  resume_filename: string
  resume_text: string
  education: Array<{
    school: string
    degree: string
    major: string
    gpa?: string
    start_date: string
    end_date: string
  }>
  experience: Array<{
    company: string
    title: string
    start_date: string
    end_date: string
    description: string
  }>
  skills: string[]
  projects: Array<{
    name: string
    description: string
    url?: string
  }>
}

interface StepResumeProps {
  initialData?: Partial<ResumeData>
  onNext: (data: ResumeData) => void
  onBack: () => void
  loading?: boolean
  onUpload: (file: File) => Promise<{ url: string; filename: string }>
}

export function StepResume({ initialData, onNext, onBack, loading, onUpload }: StepResumeProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [formData, setFormData] = useState<ResumeData>({
    resume_url: initialData?.resume_url || '',
    resume_filename: initialData?.resume_filename || '',
    resume_text: initialData?.resume_text || '',
    education: initialData?.education || [],
    experience: initialData?.experience || [],
    skills: initialData?.skills || [],
    projects: initialData?.projects || [],
  })

  const [newSkill, setNewSkill] = useState('')

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setUploading(true)
    setUploadError(null)

    try {
      const { url, filename } = await onUpload(file)
      setFormData({
        ...formData,
        resume_url: url,
        resume_filename: filename,
        resume_text: 'Resume uploaded successfully. Please review and edit the parsed information below.',
      })
    } catch (error: any) {
      setUploadError(error.message || 'Failed to upload resume')
    } finally {
      setUploading(false)
    }
  }, [formData, onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxFiles: 1,
    disabled: uploading || loading,
  })

  const addSkill = () => {
    if (newSkill.trim() && !formData.skills.includes(newSkill.trim())) {
      setFormData({
        ...formData,
        skills: [...formData.skills, newSkill.trim()]
      })
      setNewSkill('')
    }
  }

  const removeSkill = (skill: string) => {
    setFormData({
      ...formData,
      skills: formData.skills.filter(s => s !== skill)
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.resume_url) {
      onNext(formData)
    }
  }

  return (
    <Card className="max-w-3xl mx-auto">
      <CardHeader>
        <CardTitle>Upload your resume</CardTitle>
        <CardDescription>
          We'll extract your information automatically. You can review and edit everything before continuing.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* File Upload */}
          {!formData.resume_url ? (
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
                isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
              }`}
            >
              <input {...getInputProps()} />
              <div className="space-y-4">
                <div className="text-4xl">📄</div>
                {uploading ? (
                  <p className="text-lg font-medium">Uploading...</p>
                ) : isDragActive ? (
                  <p className="text-lg font-medium">Drop your resume here</p>
                ) : (
                  <>
                    <p className="text-lg font-medium">Drag & drop your resume here</p>
                    <p className="text-sm text-muted-foreground">or click to browse</p>
                    <p className="text-xs text-muted-foreground">Supports PDF, DOC, DOCX</p>
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-secondary/10 rounded-lg">
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">✓</span>
                  <div>
                    <p className="font-medium">{formData.resume_filename}</p>
                    <p className="text-sm text-muted-foreground">Resume uploaded</p>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setFormData({ ...formData, resume_url: '', resume_filename: '' })}
                  disabled={loading}
                >
                  Change
                </Button>
              </div>

              {/* Skills Section */}
              <div className="space-y-3">
                <Label>Skills</Label>
                <div className="flex gap-2">
                  <Input
                    value={newSkill}
                    onChange={(e) => setNewSkill(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addSkill()
                      }
                    }}
                    placeholder="Add a skill (e.g., React, Python)"
                    disabled={loading}
                  />
                  <Button type="button" onClick={addSkill} variant="outline" disabled={loading}>
                    Add
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {formData.skills.map((skill) => (
                    <Badge key={skill} variant="secondary" className="px-3 py-1">
                      {skill}
                      <button
                        type="button"
                        onClick={() => removeSkill(skill)}
                        className="ml-2 hover:text-destructive"
                        disabled={loading}
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                </div>
                {formData.skills.length === 0 && (
                  <p className="text-sm text-muted-foreground">Add your technical and professional skills</p>
                )}
              </div>

              {/* Resume Text Preview (for parsing) */}
              <div className="space-y-2">
                <Label htmlFor="resume_text">Resume Text (Optional)</Label>
                <Textarea
                  id="resume_text"
                  value={formData.resume_text}
                  onChange={(e) => setFormData({ ...formData, resume_text: e.target.value })}
                  placeholder="Extracted resume text will appear here..."
                  rows={4}
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  This text will be used for job matching. Edit if needed.
                </p>
              </div>
            </div>
          )}

          {uploadError && (
            <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-md text-sm">
              {uploadError}
            </div>
          )}

          <div className="flex justify-between">
            <Button type="button" variant="outline" onClick={onBack} disabled={loading || uploading}>
              Back
            </Button>
            <Button type="submit" size="lg" disabled={!formData.resume_url || loading || uploading}>
              {loading ? 'Saving...' : 'Continue'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
