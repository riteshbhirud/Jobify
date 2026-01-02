'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { FileText, Upload, Check, X, FileUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ResumeData } from '../types'

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
  })

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0]
      if (!file) return

      setUploading(true)
      setUploadError(null)

      try {
        const { url, filename } = await onUpload(file)
        setFormData({
          resume_url: url,
          resume_filename: filename,
        })
      } catch (error: any) {
        setUploadError(error.message || 'Failed to upload resume')
      } finally {
        setUploading(false)
      }
    },
    [onUpload]
  )

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onNext(formData)
  }

  const removeResume = () => {
    setFormData({
      resume_url: '',
      resume_filename: '',
    })
    setUploadError(null)
  }

  return (
    <Card className="max-w-3xl mx-auto shadow-lg border-0 bg-card/80 backdrop-blur">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center mb-4">
          <FileText className="h-7 w-7 text-primary" />
        </div>
        <CardTitle className="text-2xl">Upload Your Resume</CardTitle>
        <CardDescription className="text-base">
          Your resume will be used to auto-fill job applications
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <form onSubmit={handleSubmit} className="space-y-6">
          {!formData.resume_url ? (
            <div
              {...getRootProps()}
              className={`
                relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer
                transition-all duration-300 ease-out
                ${isDragActive
                  ? 'border-primary bg-primary/5 scale-[1.02] shadow-lg'
                  : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30'
                }
                ${uploading ? 'opacity-60 cursor-not-allowed' : ''}
              `}
            >
              <input {...getInputProps()} />
              <div className="space-y-4">
                <div className={`
                  mx-auto w-20 h-20 rounded-2xl flex items-center justify-center
                  transition-all duration-300
                  ${isDragActive ? 'bg-primary/20' : 'bg-muted'}
                `}>
                  <FileUp className={`h-10 w-10 ${isDragActive ? 'text-primary' : 'text-muted-foreground'} ${uploading ? 'animate-bounce' : ''}`} />
                </div>
                {uploading ? (
                  <>
                    <p className="text-xl font-semibold">Uploading...</p>
                    <p className="text-muted-foreground">This may take a moment</p>
                  </>
                ) : isDragActive ? (
                  <>
                    <p className="text-xl font-semibold text-primary">Drop your resume here</p>
                    <p className="text-muted-foreground">Release to upload</p>
                  </>
                ) : (
                  <>
                    <p className="text-xl font-semibold">Drag & drop your resume</p>
                    <p className="text-muted-foreground">
                      or <span className="text-primary font-medium cursor-pointer hover:underline">click to browse</span>
                    </p>
                    <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                      <span className="px-2 py-1 bg-muted rounded">PDF</span>
                      <span className="px-2 py-1 bg-muted rounded">DOC</span>
                      <span className="px-2 py-1 bg-muted rounded">DOCX</span>
                      <span className="text-xs">(max 10MB)</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-5 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-900 rounded-xl">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-green-100 dark:bg-green-900/50 flex items-center justify-center">
                    <Check className="h-6 w-6 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <p className="font-semibold text-green-900 dark:text-green-100">{formData.resume_filename}</p>
                    <p className="text-sm text-green-700 dark:text-green-300">Uploaded successfully</p>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={removeResume}
                  disabled={loading}
                  className="text-green-700 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
                >
                  <X className="h-4 w-4 mr-1" />
                  Remove
                </Button>
              </div>

              <p className="text-sm text-muted-foreground text-center">
                Your resume will be parsed automatically to fill job applications
              </p>
            </div>
          )}

          {uploadError && (
            <div className="flex items-center gap-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 px-4 py-3 rounded-xl text-sm">
              <X className="h-5 w-5 flex-shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}

          {!formData.resume_url && (
            <p className="text-sm text-muted-foreground text-center">
              You can skip this step and add your resume later
            </p>
          )}

          <div className="flex justify-between pt-6">
            <Button type="button" variant="ghost" onClick={onBack} disabled={loading || uploading}>
              Back
            </Button>
            <Button type="submit" disabled={loading || uploading} className="px-8">
              {loading ? 'Saving...' : 'Continue'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
