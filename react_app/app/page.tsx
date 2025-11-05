'use client'

import { useState, useEffect, useRef } from 'react'
import { generatePlan, getPlanStatus, generateBlog, getBlogStatus } from '@/lib/api'
import { PlanStatusResponse, BlogStatusResponse, JobStatus, BlogPlan } from '@/types/api'
import LoadingScreen from '@/components/LoadingScreen'
import PlanReviewScreen from '@/components/PlanReviewScreen'
import ReactMarkdown from 'react-markdown'

export default function Home() {
  const [mode, setMode] = useState<'quick' | 'detailed'>('quick')
  const [topic, setTopic] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [planStatus, setPlanStatus] = useState<PlanStatusResponse | null>(null)
  const [blogJobId, setBlogJobId] = useState<string | null>(null)
  const [blogStatus, setBlogStatus] = useState<BlogStatusResponse | null>(null)
  const [isGeneratingBlog, setIsGeneratingBlog] = useState(false)
  const [isReadMode, setIsReadMode] = useState(true)
  const [editedBlogContent, setEditedBlogContent] = useState<string>('')
  const pollingIntervalRef = useRef<number | null>(null)
  const blogPollingIntervalRef = useRef<number | null>(null)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current !== null) {
        clearInterval(pollingIntervalRef.current)
      }
      if (blogPollingIntervalRef.current !== null) {
        clearInterval(blogPollingIntervalRef.current)
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

  // Poll for blog generation job status
  useEffect(() => {
    if (!blogJobId || !isGeneratingBlog) return

    const pollBlogStatus = async () => {
      try {
        const status = await getBlogStatus(blogJobId)
        setBlogStatus(status)

        if (status.status === JobStatus.COMPLETED || status.status === JobStatus.FAILED) {
          setIsGeneratingBlog(false)
          if (blogPollingIntervalRef.current !== null) {
            clearInterval(blogPollingIntervalRef.current)
            blogPollingIntervalRef.current = null
          }
        }
      } catch (error) {
        console.error('Error polling blog job status:', error)
        setIsGeneratingBlog(false)
        if (blogPollingIntervalRef.current !== null) {
          clearInterval(blogPollingIntervalRef.current)
          blogPollingIntervalRef.current = null
        }
        alert('Error checking blog generation status. Please try again.')
      }
    }

    // Poll immediately, then every 2 seconds
    pollBlogStatus()
    blogPollingIntervalRef.current = window.setInterval(pollBlogStatus, 2000)
  }, [blogJobId, isGeneratingBlog])

  // Initialize edited content when blog status changes
  useEffect(() => {
    if (blogStatus?.status === JobStatus.COMPLETED && blogStatus.blog && editedBlogContent === '') {
      setEditedBlogContent(blogStatus.blog)
    }
  }, [blogStatus?.blog, blogStatus?.status])

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

  const handleGenerateBlog = async (plan: BlogPlan) => {
    try {
      setIsGeneratingBlog(true)
      setBlogStatus(null)
      
      // Generate session ID
      const sessionId = crypto.randomUUID()
      
      // Call generate-blog API with plan and plan_job_id if available
      const response = await generateBlog(sessionId, { 
        plan,
        plan_job_id: jobId || undefined
      })
      setBlogJobId(response.job_id)
      
      // Polling will be handled by useEffect
    } catch (error) {
      console.error('Error generating blog:', error)
      setIsGeneratingBlog(false)
      alert(error instanceof Error ? error.message : 'Failed to generate blog. Please try again.')
    }
  }

  // Show loading screen while generating blog
  if (isGeneratingBlog) {
    const loadingMessage = blogStatus?.status === JobStatus.PROCESSING
      ? 'Generating your blog post...'
      : 'Starting blog generation...'
    return <LoadingScreen message={loadingMessage} />
  }

  const handleExportBlog = () => {
    const contentToExport = isReadMode ? blogStatus?.blog : editedBlogContent
    if (!contentToExport) return
    
    const blob = new Blob([contentToExport], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    // Extract title from markdown (first # heading)
    const titleMatch = contentToExport.match(/^#\s+(.+)$/m)
    const filename = titleMatch 
      ? `${titleMatch[1].replace(/[^a-z0-9]/gi, '_').toLowerCase()}.md`
      : 'blog_post.md'
    
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  // Show blog result if completed
  if (blogStatus?.status === JobStatus.COMPLETED && blogStatus.blog) {
    // Use edited content if available, otherwise use original blog content
    const displayContent = editedBlogContent || blogStatus.blog

    return (
      <div className="min-h-screen flex flex-col bg-background">
        <header className="flex justify-between items-center px-8 py-6 border-b border-input-bg">
          <div className="flex items-center gap-2">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="text-accent"
            >
              <path
                d="M4 19.5V4.5C4 3.897 4.447 3.5 5 3.5H19C19.553 3.5 20 3.897 20 4.5V19.5C20 20.103 19.553 20.5 19 20.5H5C4.447 20.5 4 20.103 4 19.5Z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M4 8L12 13L20 8"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span className="text-text-primary text-xl font-semibold">
              AI Blog Writer
            </span>
          </div>
        </header>
        <main className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-4xl mx-auto">
            {/* Action Bar */}
            <div className="mb-6 flex items-center justify-between">
              <button
                onClick={() => {
                  setBlogStatus(null)
                  setBlogJobId(null)
                }}
                className="px-4 py-2 text-text-secondary hover:text-accent transition-colors flex items-center gap-2"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  className="text-current"
                >
                  <path
                    d="M19 12H5M5 12L12 19M5 12L12 5"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                Back to Plan
              </button>
              
              <div className="flex items-center gap-3">
                {/* Read/Edit Mode Toggle */}
                <div className="flex items-center gap-2 bg-input-bg rounded-lg p-1">
                  <button
                    onClick={() => setIsReadMode(true)}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                      isReadMode
                        ? 'bg-accent text-text-primary'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          d="M2 3H8C9.06087 3 10.0783 3.42143 10.8284 4.17157C11.5786 4.92172 12 5.93913 12 7V21C12 20.2044 11.6839 19.4413 11.1213 18.8787C10.5587 18.3161 9.79565 18 9 18H2V3Z"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        <path
                          d="M22 3H16C14.9391 3 13.9217 3.42143 13.1716 4.17157C12.4214 4.92172 12 5.93913 12 7V21C12 20.2044 12.3161 19.4413 12.8787 18.8787C13.4413 18.3161 14.2044 18 15 18H22V3Z"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      Read Mode
                    </div>
                  </button>
                  <button
                    onClick={() => setIsReadMode(false)}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                      !isReadMode
                        ? 'bg-accent text-text-primary'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        <path
                          d="M18.5 2.5C18.8978 2.10218 19.4374 1.87868 20 1.87868C20.5626 1.87868 21.1022 2.10218 21.5 2.5C21.8978 2.89782 22.1213 3.43739 22.1213 4C22.1213 4.56261 21.8978 5.10218 21.5 5.5L12 15L8 16L9 12L18.5 2.5Z"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      Edit Mode
                    </div>
                  </button>
                </div>

                {/* Export Button */}
                <button
                  onClick={handleExportBlog}
                  className="px-4 py-2 bg-accent text-text-primary rounded-lg font-medium hover:bg-opacity-90 transition-all flex items-center gap-2"
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M7 10L12 15L17 10"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M12 15V3"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  Export
                </button>
              </div>
            </div>

            {/* Blog Content */}
            <div className="bg-input-bg/50 rounded-lg border border-input-bg overflow-hidden">
              {isReadMode ? (
                <div className="p-8 prose prose-invert prose-lg max-w-none">
                  <ReactMarkdown
                    components={{
                      h1: ({ node, ...props }) => (
                        <h1 className="text-4xl font-bold text-text-primary mb-4 mt-8 first:mt-0" {...props} />
                      ),
                      h2: ({ node, ...props }) => (
                        <h2 className="text-3xl font-bold text-text-primary mb-3 mt-6" {...props} />
                      ),
                      h3: ({ node, ...props }) => (
                        <h3 className="text-2xl font-semibold text-text-primary mb-2 mt-4" {...props} />
                      ),
                      p: ({ node, ...props }) => (
                        <p className="text-text-secondary leading-relaxed mb-4" {...props} />
                      ),
                      ul: ({ node, ...props }) => (
                        <ul className="list-disc list-inside mb-4 text-text-secondary space-y-2" {...props} />
                      ),
                      ol: ({ node, ...props }) => (
                        <ol className="list-decimal list-inside mb-4 text-text-secondary space-y-2" {...props} />
                      ),
                      li: ({ node, ...props }) => (
                        <li className="text-text-secondary" {...props} />
                      ),
                      strong: ({ node, ...props }) => (
                        <strong className="font-semibold text-text-primary" {...props} />
                      ),
                      code: ({ node, inline, ...props }: any) => {
                        if (inline) {
                          return (
                            <code className="bg-background px-1.5 py-0.5 rounded text-accent text-sm font-mono" {...props} />
                          )
                        }
                        return (
                          <code className="block bg-background p-4 rounded-lg text-text-primary text-sm font-mono overflow-x-auto mb-4" {...props} />
                        )
                      },
                    }}
                  >
                    {displayContent}
                  </ReactMarkdown>
                </div>
              ) : (
                <div className="p-8">
                  <textarea
                    value={editedBlogContent}
                    onChange={(e) => setEditedBlogContent(e.target.value)}
                    className="w-full min-h-[600px] bg-background text-text-primary font-mono text-sm leading-relaxed p-4 rounded-lg border border-input-bg focus:outline-none focus:ring-2 focus:ring-accent resize-y"
                    placeholder="Edit your blog post markdown here..."
                  />
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    )
  }

  // Show error if blog generation failed
  if (blogStatus?.status === JobStatus.FAILED) {
    return (
      <div className="min-h-screen flex flex-col bg-background items-center justify-center px-8">
        <div className="max-w-2xl w-full text-center">
          <h1 className="text-3xl font-bold text-text-primary mb-4">
            Blog Generation Failed
          </h1>
          <p className="text-text-secondary mb-8">
            {blogStatus.error || 'An unknown error occurred'}
          </p>
          <button
            onClick={() => {
              setBlogStatus(null)
              setBlogJobId(null)
            }}
            className="px-6 py-3 bg-accent text-text-primary rounded-lg font-semibold hover:bg-opacity-90 transition-all"
          >
            Back to Plan
          </button>
        </div>
      </div>
    )
  }

  // Show loading screen while processing plan
  if (isLoading) {
    const loadingMessage = planStatus?.status === JobStatus.PROCESSING
      ? 'Researching keywords...'
      : 'Processing your request...'
    return <LoadingScreen message={loadingMessage} />
  }

  // Show review screen if plan completed
  if (planStatus?.status === JobStatus.COMPLETED && planStatus.plan) {
    return (
      <PlanReviewScreen
        plan={planStatus.plan}
        onBack={() => {
          setPlanStatus(null)
          setJobId(null)
          setTopic('')
        }}
        onGenerate={handleGenerateBlog}
      />
    )
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
      {/* Header */}
      <header className="flex justify-between items-center px-8 py-6">
        <div className="flex items-center gap-2">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="text-accent"
          >
            <path
              d="M4 19.5V4.5C4 3.897 4.447 3.5 5 3.5H19C19.553 3.5 20 3.897 20 4.5V19.5C20 20.103 19.553 20.5 19 20.5H5C4.447 20.5 4 20.103 4 19.5Z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M4 8L12 13L20 8"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="text-text-primary text-xl font-semibold">
            AI Blog Writer
          </span>
        </div>
        <div className="w-10 h-10 rounded-full border-2 border-text-secondary flex items-center justify-center">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="text-text-secondary"
          >
            <path
              d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21M16 7C16 9.20914 14.2091 11 12 11C9.79086 11 8 9.20914 8 7C8 4.79086 9.79086 3 12 3C14.2091 3 16 4.79086 16 7Z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </header>

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

