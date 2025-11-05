'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { getBlogStatus } from '@/lib/api'
import { BlogStatusResponse, JobStatus } from '@/types/api'
import { useAuth } from '@/components/AuthProvider'
import LoadingScreen from '@/components/LoadingScreen'
import ReactMarkdown from 'react-markdown'
import Header from '@/components/Header'

export default function BlogPage() {
  const params = useParams()
  const router = useRouter()
  const blogId = params.id as string
  const { user, loading: authLoading } = useAuth()
  
  const [blogStatus, setBlogStatus] = useState<BlogStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isReadMode, setIsReadMode] = useState(true)
  const [editedBlogContent, setEditedBlogContent] = useState<string>('')
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Redirect to auth if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/auth')
    }
  }, [user, authLoading, router])

  useEffect(() => {
    if (!blogId) return

    const fetchBlog = async () => {
      try {
        const status = await getBlogStatus(blogId)
        setBlogStatus(status)
        
        // If blog is completed or failed, stop loading and polling
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
        console.error('Error fetching blog:', error)
        setIsLoading(false)
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
        alert('Error loading blog. Please try again.')
      }
    }

    fetchBlog()
    
    // Poll every 2 seconds if still processing
    pollingIntervalRef.current = setInterval(() => {
      fetchBlog()
    }, 2000)
    
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
    }
  }, [blogId])

  // Initialize edited content when blog status changes
  useEffect(() => {
    if (blogStatus?.status === JobStatus.COMPLETED && blogStatus.blog && editedBlogContent === '') {
      setEditedBlogContent(blogStatus.blog)
    }
  }, [blogStatus?.blog, blogStatus?.status])

  const handleExportBlog = () => {
    const contentToExport = editedBlogContent || blogStatus?.blog
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

  // Show loading screen while checking auth
  if (authLoading) {
    return <LoadingScreen message="Loading..." />
  }

  // Don't render if not authenticated (will redirect)
  if (!user) {
    return null
  }

  if (isLoading) {
    const loadingMessage = blogStatus?.status === JobStatus.PROCESSING
      ? 'Generating your blog post...'
      : 'Loading blog...'
    return <LoadingScreen message={loadingMessage} />
  }

  // Show error if failed
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
            onClick={() => router.push('/')}
            className="px-6 py-3 bg-accent text-text-primary rounded-lg font-semibold hover:bg-opacity-90 transition-all"
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  // Show blog result if completed
  if (blogStatus?.status === JobStatus.COMPLETED && blogStatus.blog) {
    // Use edited content if available, otherwise use original blog content
    const displayContent = editedBlogContent || blogStatus.blog

    return (
      <div className="min-h-screen flex flex-col bg-background">
        <Header showBackButton backUrl={blogStatus?.plan_job_id ? `/plan/${blogStatus.plan_job_id}` : '/'} backLabel={blogStatus?.plan_job_id ? 'Back to Plan' : 'Back to Home'} />
        <main className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-4xl mx-auto">
            {/* Action Bar */}
            <div className="mb-6 flex items-center justify-end">
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

  // Show loading if still processing
  return <LoadingScreen message="Loading blog..." />
}

