'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { ProgressBar } from '@/components/onboarding/ProgressBar'
import { StepPersonalInfo } from '@/components/onboarding/steps/StepPersonalInfo'
import { StepEducation } from '@/components/onboarding/steps/StepEducation'
import { StepExperience } from '@/components/onboarding/steps/StepExperience'
import { StepSkillsAndProjects } from '@/components/onboarding/steps/StepSkillsAndProjects'
import { StepResume } from '@/components/onboarding/steps/StepResume'
import { StepPreferences } from '@/components/onboarding/steps/StepPreferences'
import { StepAutomation } from '@/components/onboarding/steps/StepAutomation'
import { CompletionScreen } from '@/components/onboarding/CompletionScreen'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Logo } from '@/components/shared/Logo'

const TOTAL_STEPS = 7

const STEP_TITLES = [
  'Personal Information',
  'Education',
  'Work Experience',
  'Skills & Projects',
  'Resume',
  'Job Preferences',
  'Automation Settings',
]

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [userData, setUserData] = useState<any>({})
  const [userId, setUserId] = useState<string | null>(null)
  const [userEmail, setUserEmail] = useState<string>('')

  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    loadUserData()
  }, [])

  const loadUserData = async () => {
    try {
      const {
        data: { user },
      } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }

      setUserId(user.id)
      setUserEmail(user.email || '')

      const { data: profile } = await supabase
        .from('users')
        .select('*')
        .eq('id', user.id)
        .single()

      if (profile) {
        setUserData(profile)
        // Resume from last step if partially completed
        if (profile.onboarding_step) {
          setCurrentStep(profile.onboarding_step)
        }
        // If already completed, redirect to dashboard
        if (profile.onboarding_completed) {
          router.push('/dashboard')
        }
      }
    } catch (error) {
      console.error('Error loading user data:', error)
    } finally {
      setLoading(false)
    }
  }

  const saveData = async (data: any, nextStep: number) => {
    if (!userId) return

    setSaving(true)
    try {
      const { error } = await supabase
        .from('users')
        .update({
          ...data,
          onboarding_step: nextStep,
          updated_at: new Date().toISOString(),
        })
        .eq('id', userId)

      if (error) throw error

      setUserData({ ...userData, ...data })
      setCurrentStep(nextStep)

      // Scroll to top when changing steps
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (error: any) {
      console.error('Error saving data:', error)
      alert('Failed to save data. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const completeOnboarding = async (data: any) => {
    if (!userId) return

    setSaving(true)
    try {
      const { error } = await supabase
        .from('users')
        .update({
          ...data,
          onboarding_step: TOTAL_STEPS + 1,
          onboarding_completed: true,
          is_active: false, // User will manually activate from dashboard
          updated_at: new Date().toISOString(),
        })
        .eq('id', userId)

      if (error) throw error

      setUserData({ ...userData, ...data })
      setCurrentStep(TOTAL_STEPS + 1) // Show completion screen
    } catch (error: any) {
      console.error('Error completing onboarding:', error)
      alert('Failed to complete onboarding. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const handleResumeUpload = async (file: File) => {
    if (!userId) throw new Error('No user ID')

    // Validate file size (max 10MB)
    const maxSize = 10 * 1024 * 1024 // 10MB
    if (file.size > maxSize) {
      throw new Error('File size exceeds 10MB limit')
    }

    // Validate file type
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ]
    if (!allowedTypes.includes(file.type)) {
      throw new Error('Only PDF, DOC, and DOCX files are allowed')
    }

    // Create unique filename with timestamp to avoid conflicts
    const timestamp = Date.now()
    const fileExt = file.name.split('.').pop()
    const fileName = `resume_${timestamp}.${fileExt}`
    const filePath = `${userId}/${fileName}`

    // Upload to Supabase Storage
    const { data, error } = await supabase.storage.from('resumes').upload(filePath, file, {
      upsert: true,
      contentType: file.type,
    })

    if (error) {
      console.error('Upload error:', error)
      throw new Error(`Upload failed: ${error.message}`)
    }

    // Get the public URL
    const { data: urlData } = supabase.storage.from('resumes').getPublicUrl(filePath)

    return {
      url: urlData.publicUrl,
      filename: file.name, // Keep original filename for display
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  const isCompleted = currentStep > TOTAL_STEPS

  return (
    <div className="min-h-screen bg-gradient-to-b from-primary/5 via-background to-background py-8 px-4">
      <div className="container mx-auto max-w-4xl">
        {/* Header */}
        <div className="text-center mb-8">
          <Logo className="inline-block mb-4" />
          {!isCompleted && (
            <>
              <h1 className="text-2xl md:text-3xl font-bold mb-2">{STEP_TITLES[currentStep - 1]}</h1>
              <p className="text-muted-foreground">
                Step {currentStep} of {TOTAL_STEPS}
              </p>
            </>
          )}
        </div>

        {/* Progress Bar */}
        {!isCompleted && <ProgressBar currentStep={currentStep} totalSteps={TOTAL_STEPS} />}

        {/* Step Components */}
        {currentStep === 1 && (
          <StepPersonalInfo
            initialData={userData}
            userEmail={userEmail}
            onNext={(data) => saveData(data, 2)}
            loading={saving}
          />
        )}

        {currentStep === 2 && (
          <StepEducation
            initialData={userData}
            onNext={(data) => saveData(data, 3)}
            onBack={() => setCurrentStep(1)}
            loading={saving}
          />
        )}

        {currentStep === 3 && (
          <StepExperience
            initialData={userData}
            onNext={(data) => saveData(data, 4)}
            onBack={() => setCurrentStep(2)}
            loading={saving}
          />
        )}

        {currentStep === 4 && (
          <StepSkillsAndProjects
            initialData={userData}
            onNext={(data) => saveData(data, 5)}
            onBack={() => setCurrentStep(3)}
            loading={saving}
          />
        )}

        {currentStep === 5 && (
          <StepResume
            initialData={userData}
            onNext={(data) => saveData(data, 6)}
            onBack={() => setCurrentStep(4)}
            onUpload={handleResumeUpload}
            loading={saving}
          />
        )}

        {currentStep === 6 && (
          <StepPreferences
            initialData={userData}
            onNext={(data) => saveData(data, 7)}
            onBack={() => setCurrentStep(5)}
            loading={saving}
          />
        )}

        {currentStep === 7 && (
          <StepAutomation
            initialData={userData}
            onNext={(data) => completeOnboarding(data)}
            onBack={() => setCurrentStep(6)}
            loading={saving}
          />
        )}

        {isCompleted && <CompletionScreen userData={userData} />}
      </div>
    </div>
  )
}
