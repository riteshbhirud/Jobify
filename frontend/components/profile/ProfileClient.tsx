'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { BasicInfoSection } from './sections/BasicInfoSection'
import { ResumeSection } from './sections/ResumeSection'
import { ProfessionalSection } from './sections/ProfessionalSection'
import { PreferencesSection } from './sections/PreferencesSection'
import { AutomationSection } from './sections/AutomationSection'

interface ProfileClientProps {
  profile: any
  userId: string
  userEmail: string
}

export function ProfileClient({ profile, userId, userEmail }: ProfileClientProps) {
  const [editingSection, setEditingSection] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const router = useRouter()
  const supabase = createClient()

  const showFeedback = (type: 'success' | 'error', message: string) => {
    setFeedback({ type, message })
    setTimeout(() => setFeedback(null), 4000)
  }

  const saveSection = async (sectionData: Record<string, any>) => {
    setSaving(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) throw new Error('Not authenticated')

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/users/me`,
        {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(sectionData),
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to update profile')
      }

      const result = await response.json()

      if (result.embedding_updated) {
        showFeedback('success', 'Profile updated. Your job matching profile has been refreshed.')
      } else {
        showFeedback('success', 'Profile updated successfully.')
      }

      setEditingSection(null)
      router.refresh()
    } catch (error: any) {
      showFeedback('error', error.message || 'Failed to update profile')
      throw error
    } finally {
      setSaving(false)
    }
  }

  const handleResumeUpload = async (file: File) => {
    const maxSize = 10 * 1024 * 1024
    if (file.size > maxSize) {
      throw new Error('File size exceeds 10MB limit')
    }

    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ]
    if (!allowedTypes.includes(file.type)) {
      throw new Error('Only PDF, DOC, and DOCX files are allowed')
    }

    const timestamp = Date.now()
    const fileExt = file.name.split('.').pop()
    const fileName = `resume_${timestamp}.${fileExt}`
    const filePath = `${userId}/${fileName}`

    const { error } = await supabase.storage.from('resumes').upload(filePath, file, {
      upsert: true,
      contentType: file.type,
    })

    if (error) {
      throw new Error(`Upload failed: ${error.message}`)
    }

    const { data: urlData } = supabase.storage.from('resumes').getPublicUrl(filePath)

    await saveSection({
      resume_url: urlData.publicUrl,
      resume_filename: file.name,
    })
  }

  const handleEdit = (section: string) => {
    setEditingSection(section)
    setFeedback(null)
  }

  const handleCancel = () => {
    setEditingSection(null)
  }

  return (
    <div className="space-y-6">
      {feedback && (
        <div
          className={`p-4 rounded-lg text-sm ${
            feedback.type === 'success'
              ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-900'
              : 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-900'
          }`}
        >
          {feedback.message}
        </div>
      )}

      <BasicInfoSection
        profile={profile}
        userEmail={userEmail}
        isEditing={editingSection === 'basic'}
        onEdit={() => handleEdit('basic')}
        onSave={saveSection}
        onCancel={handleCancel}
        saving={saving}
      />

      <ResumeSection
        profile={profile}
        onUpload={handleResumeUpload}
        saving={saving}
      />

      <ProfessionalSection
        profile={profile}
        onSave={saveSection}
        saving={saving}
      />

      <PreferencesSection
        profile={profile}
        isEditing={editingSection === 'preferences'}
        onEdit={() => handleEdit('preferences')}
        onSave={saveSection}
        onCancel={handleCancel}
        saving={saving}
      />

      <AutomationSection
        profile={profile}
        isEditing={editingSection === 'automation'}
        onEdit={() => handleEdit('automation')}
        onSave={saveSection}
        onCancel={handleCancel}
        saving={saving}
      />
    </div>
  )
}
