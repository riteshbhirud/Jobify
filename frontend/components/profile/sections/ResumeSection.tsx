'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { FileText, FileUp, Check, X, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface ResumeSectionProps {
  profile: any
  onUpload: (file: File) => Promise<void>
  saving: boolean
}

export function ResumeSection({ profile, onUpload, saving }: ResumeSectionProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [showDropzone, setShowDropzone] = useState(!profile?.resume_url)

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0]
      if (!file) return

      setUploading(true)
      setUploadError(null)

      try {
        await onUpload(file)
        setShowDropzone(false)
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
    disabled: uploading || saving,
  })

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Resume
          </CardTitle>
          <CardDescription>Your resume used for job applications</CardDescription>
        </div>
        {profile?.resume_url && !showDropzone && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowDropzone(true)}
            disabled={saving}
          >
            Replace Resume
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {profile?.resume_url && !showDropzone && (
          <div className="flex items-center justify-between p-4 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-900 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/50 flex items-center justify-center">
                <Check className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="font-medium text-green-900 dark:text-green-100">
                  {profile.resume_filename || 'Resume uploaded'}
                </p>
                <p className="text-sm text-green-700 dark:text-green-300">Uploaded</p>
              </div>
            </div>
            <a
              href={profile.resume_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-green-700 dark:text-green-300 hover:text-green-900 dark:hover:text-green-100"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
        )}

        {showDropzone && (
          <div
            {...getRootProps()}
            className={`
              relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
              transition-all duration-300 ease-out
              ${isDragActive
                ? 'border-primary bg-primary/5 scale-[1.01]'
                : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30'
              }
              ${uploading ? 'opacity-60 cursor-not-allowed' : ''}
            `}
          >
            <input {...getInputProps()} />
            <div className="space-y-3">
              <div className={`
                mx-auto w-14 h-14 rounded-xl flex items-center justify-center
                ${isDragActive ? 'bg-primary/20' : 'bg-muted'}
              `}>
                <FileUp className={`h-7 w-7 ${isDragActive ? 'text-primary' : 'text-muted-foreground'} ${uploading ? 'animate-bounce' : ''}`} />
              </div>
              {uploading ? (
                <p className="font-medium">Uploading...</p>
              ) : isDragActive ? (
                <p className="font-medium text-primary">Drop your resume here</p>
              ) : (
                <>
                  <p className="font-medium">Drag & drop your resume</p>
                  <p className="text-sm text-muted-foreground">
                    or <span className="text-primary font-medium cursor-pointer hover:underline">click to browse</span>
                  </p>
                  <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <span className="px-2 py-0.5 bg-muted rounded text-xs">PDF</span>
                    <span className="px-2 py-0.5 bg-muted rounded text-xs">DOC</span>
                    <span className="px-2 py-0.5 bg-muted rounded text-xs">DOCX</span>
                    <span className="text-xs">(max 10MB)</span>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {showDropzone && profile?.resume_url && (
          <div className="flex justify-end">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setShowDropzone(false)
                setUploadError(null)
              }}
            >
              Cancel
            </Button>
          </div>
        )}

        {uploadError && (
          <div className="flex items-center gap-2 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg text-sm">
            <X className="h-4 w-4 flex-shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
