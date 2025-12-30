'use client'

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { createClient } from "@/lib/supabase/client"
import { ProgressBar } from "@/components/onboarding/ProgressBar"
import { StepBasicInfo } from "@/components/onboarding/StepBasicInfo"
import { StepLocation } from "@/components/onboarding/StepLocation"
import { StepResume } from "@/components/onboarding/StepResume"
import { StepPreferences } from "@/components/onboarding/StepPreferences"
import { StepAutomation } from "@/components/onboarding/StepAutomation"
import { CompletionScreen } from "@/components/onboarding/CompletionScreen"
import { LoadingSpinner } from "@/components/shared/LoadingSpinner"
import { Logo } from "@/components/shared/Logo"

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [userData, setUserData] = useState<any>({})
  const [userId, setUserId] = useState<string | null>(null)

  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    loadUserData()
  }, [])

  const loadUserData = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }

      setUserId(user.id)

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
        })
        .eq('id', userId)

      if (error) throw error

      setUserData({ ...userData, ...data })
      setCurrentStep(nextStep)
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
          onboarding_step: 6,
          onboarding_completed: true,
          is_active: true,
        })
        .eq('id', userId)

      if (error) throw error

      setUserData({ ...userData, ...data })
      setCurrentStep(6)
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
    const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    if (!allowedTypes.includes(file.type)) {
      throw new Error('Only PDF, DOC, and DOCX files are allowed')
    }

    // Create unique filename with timestamp to avoid conflicts
    const timestamp = Date.now()
    const fileExt = file.name.split('.').pop()
    const fileName = `resume_${timestamp}.${fileExt}`
    const filePath = `${userId}/${fileName}`

    // Upload to Supabase Storage
    const { data, error } = await supabase.storage
      .from('resumes')
      .upload(filePath, file, {
        upsert: true,
        contentType: file.type
      })

    if (error) {
      console.error('Upload error:', error)
      throw new Error(`Upload failed: ${error.message}`)
    }

    // Get the public URL
    const { data: urlData } = supabase.storage
      .from('resumes')
      .getPublicUrl(filePath)

    return {
      url: urlData.publicUrl,
      filename: file.name // Keep original filename for display
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-primary/5 to-background py-12 px-4">
      <div className="container mx-auto max-w-4xl">
        <div className="text-center mb-12">
          <Logo className="inline-block mb-4" />
          <h1 className="text-3xl font-bold mb-2">Welcome to Jobify</h1>
          <p className="text-muted-foreground">Let's get you set up in just a few minutes</p>
        </div>

        {currentStep < 6 && <ProgressBar currentStep={currentStep} totalSteps={5} />}

        {currentStep === 1 && (
          <StepBasicInfo
            initialData={userData}
            onNext={(data) => saveData(data, 2)}
            loading={saving}
          />
        )}

        {currentStep === 2 && (
          <StepLocation
            initialData={userData}
            onNext={(data) => saveData(data, 3)}
            onBack={() => setCurrentStep(1)}
            loading={saving}
          />
        )}

        {currentStep === 3 && (
          <StepResume
            initialData={userData}
            onNext={(data) => saveData(data, 4)}
            onBack={() => setCurrentStep(2)}
            onUpload={handleResumeUpload}
            loading={saving}
          />
        )}

        {currentStep === 4 && (
          <StepPreferences
            initialData={userData}
            onNext={(data) => saveData(data, 5)}
            onBack={() => setCurrentStep(3)}
            loading={saving}
          />
        )}

        {currentStep === 5 && (
          <StepAutomation
            initialData={userData}
            onNext={(data) => completeOnboarding(data)}
            onBack={() => setCurrentStep(4)}
            loading={saving}
          />
        )}

        {currentStep === 6 && (
          <CompletionScreen userData={userData} />
        )}
      </div>
    </div>
  )
}
