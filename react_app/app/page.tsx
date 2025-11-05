'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { generatePlan, getPlanStatus } from '@/lib/api'
import { PlanStatusResponse, JobStatus } from '@/types/api'
import { useAuth } from '@/components/AuthProvider'
import LoadingScreen from '@/components/LoadingScreen'
import Header from '@/components/Header'

export default function Home() {
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  const [mode, setMode] = useState<'quick' | 'detailed'>('quick')
  const [topic, setTopic] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [planStatus, setPlanStatus] = useState<PlanStatusResponse | null>(null)
  const pollingIntervalRef = useRef<number | null>(null)

  // Redirect to auth if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/auth')
    }
  }, [user, authLoading, router])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current !== null) {
        clearInterval(pollingIntervalRef.current)
      }
    }
  }, [])

  // Poll for job status
  useEffect(() => {
    if (!jobId || !isLoading) return

    const pollStatus = async () => {
      try {
        const status = await getPlanStatus(jobId)
        setPlanStatus(status)

        if (status.status === JobStatus.COMPLETED || status.status === JobStatus.FAILED) {
          setIsLoading(false)
          if (pollingIntervalRef.current !== null) {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
          }
          
          // Navigate to plan page when completed
          if (status.status === JobStatus.COMPLETED) {
            router.push(`/plan/${jobId}`)
          }
        }
      } catch (error) {
        console.error('Error polling job status:', error)
        setIsLoading(false)
        if (pollingIntervalRef.current !== null) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
        alert('Error checking job status. Please try again.')
      }
    }

    // Poll immediately, then every 2 seconds
    pollStatus()
    pollingIntervalRef.current = window.setInterval(pollStatus, 2000)
  }, [jobId, isLoading])


  const handleGenerate = async () => {
    if (!topic.trim()) {
      alert('Please enter a topic or keywords')
      return
    }

    try {
      setIsLoading(true)
      setPlanStatus(null)
      
      // Generate session ID
      const sessionId = crypto.randomUUID()
      
      // Call generate-plan API
      const response = await generatePlan(sessionId, { keyword: topic })
      setJobId(response.job_id)
      
      // Polling will be handled by useEffect
    } catch (error) {
      console.error('Error generating plan:', error)
      setIsLoading(false)
      alert(error instanceof Error ? error.message : 'Failed to generate plan. Please try again.')
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

  // Show loading screen while processing plan
  if (isLoading) {
    const loadingMessage = planStatus?.status === JobStatus.PROCESSING
      ? 'Researching keywords...'
      : 'Processing your request...'
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
            onClick={() => {
              setPlanStatus(null)
              setJobId(null)
            }}
            className="px-6 py-3 bg-accent text-text-primary rounded-lg font-semibold hover:bg-opacity-90 transition-all"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center px-8 py-12">
        <h1 className="text-5xl font-bold text-text-primary text-center mb-4">
          Unleash Your Next Great Blog Post
        </h1>
        <p className="text-text-secondary text-lg text-center mb-8">
          Enter a few keywords or a topic, and let our AI do the rest.
        </p>

        {/* Mode Selection */}
        {/* Input Field */}
        <div className="w-full max-w-2xl mb-6">
          <div className="relative">
            <div className="absolute left-4 top-1/2 transform -translate-y-1/2">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="text-text-secondary"
              >
                <path
                  d="M21 21L15 15M17 10C17 13.866 13.866 17 10 17C6.13401 17 3 13.866 3 10C3 6.13401 6.13401 3 10 3C13.866 3 17 6.13401 17 10Z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleGenerate()
                }
              }}
              placeholder="e.g., 'future of remote work trends'"
              className="w-full pl-12 pr-4 py-4 rounded-lg bg-input-bg text-text-primary placeholder-text-secondary focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>
        </div>

        {/* Generate Button */}
        <button
          onClick={handleGenerate}
          className="px-8 py-4 bg-accent text-text-primary rounded-lg font-semibold text-lg hover:bg-opacity-90 transition-all shadow-lg hover:shadow-xl"
        >
          Generate Blog
        </button>
      </main>

      {/* Footer */}
      <footer className="flex justify-between items-center px-8 py-6 border-t border-input-bg">
        <p className="text-text-secondary text-sm">
          © 2024 AI Blog Writer. All rights reserved.
        </p>
        <div className="flex gap-6">
          <a
            href="#"
            className="text-text-secondary text-sm hover:text-accent transition-colors"
          >
            About
          </a>
          <a
            href="#"
            className="text-text-secondary text-sm hover:text-accent transition-colors"
          >
            Privacy Policy
          </a>
          <a
            href="#"
            className="text-text-secondary text-sm hover:text-accent transition-colors"
          >
            Contact
          </a>
        </div>
      </footer>
    </div>
  )
}

