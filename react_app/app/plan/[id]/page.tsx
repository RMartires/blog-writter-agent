'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { getPlanStatus } from '@/lib/api'
import { PlanStatusResponse, JobStatus, BlogPlan } from '@/types/api'
import LoadingScreen from '@/components/LoadingScreen'
import PlanReviewScreen from '@/components/PlanReviewScreen'
import { generateBlog } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'

export default function PlanPage() {
  const params = useParams()
  const router = useRouter()
  const planId = params.id as string
  const { user, loading: authLoading } = useAuth()
  
  const [planStatus, setPlanStatus] = useState<PlanStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isGeneratingBlog, setIsGeneratingBlog] = useState(false)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Redirect to auth if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/auth')
    }
  }, [user, authLoading, router])

  useEffect(() => {
    if (!planId) return

    const fetchPlan = async () => {
      try {
        const status = await getPlanStatus(planId)
        setPlanStatus(status)
        
        // If plan is completed or failed, stop loading and polling
        if (status.status === JobStatus.COMPLETED || status.status === JobStatus.FAILED) {
          setIsLoading(false)
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
          }
        } else {
          // Keep loading if still processing
          setIsLoading(true)
        }
      } catch (error) {
        console.error('Error fetching plan:', error)
        setIsLoading(false)
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
        alert('Error loading plan. Please try again.')
      }
    }

    fetchPlan()
    
    // Poll every 2 seconds if still processing
    pollingIntervalRef.current = setInterval(() => {
      fetchPlan()
    }, 2000)
    
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
    }
  }, [planId])

  const handleGenerateBlog = async (plan: BlogPlan) => {
    try {
      setIsGeneratingBlog(true)
      
      // Generate session ID
      const sessionId = crypto.randomUUID()
      
      // Call generate-blog API with plan and plan_job_id
      const response = await generateBlog(sessionId, { 
        plan,
        plan_job_id: planId
      })
      
      // Navigate to blog page
      router.push(`/blog/${response.job_id}`)
    } catch (error) {
      console.error('Error generating blog:', error)
      setIsGeneratingBlog(false)
      alert(error instanceof Error ? error.message : 'Failed to generate blog. Please try again.')
    }
  }

  // Show loading screen while checking auth
  if (authLoading) {
    return <LoadingScreen message="Loading..." />
  }

  // Don't render if not authenticated (will redirect)
  if (!user) {
    return null
  }

  if (isLoading || isGeneratingBlog) {
    const loadingMessage = isGeneratingBlog
      ? 'Generating your blog post...'
      : planStatus?.status === JobStatus.PROCESSING
      ? 'Loading plan...'
      : 'Loading...'
    return <LoadingScreen message={loadingMessage} />
  }

  // Show error if failed
  if (planStatus?.status === JobStatus.FAILED) {
    return (
      <div className="min-h-screen flex flex-col bg-background items-center justify-center px-8">
        <div className="max-w-2xl w-full text-center">
          <h1 className="text-3xl font-bold text-text-primary mb-4">
            Plan Generation Failed
          </h1>
          <p className="text-text-secondary mb-8">
            {planStatus.error || 'An unknown error occurred'}
          </p>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-3 bg-accent text-text-primary rounded-lg font-semibold hover:bg-opacity-90 transition-all"
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  // Show review screen if completed
  if (planStatus?.status === JobStatus.COMPLETED && planStatus.plan) {
    return (
      <PlanReviewScreen
        plan={planStatus.plan}
        onBack={() => router.push('/')}
        onGenerate={handleGenerateBlog}
      />
    )
  }

  // Show loading if still processing
  return <LoadingScreen message="Loading plan..." />
}

