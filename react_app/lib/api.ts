import { GeneratePlanRequest, JobResponse, PlanStatusResponse, GenerateBlogRequest, BlogStatusResponse } from '@/types/api'
import { supabase } from './supabase'

const API_HOST = process.env.NEXT_PUBLIC_API_HOST || 'http://localhost:8000'

async function getAuthHeaders(): Promise<HeadersInit> {
  const { data: { session }, error } = await supabase.auth.getSession()
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  }
  
  if (error) {
    console.error('Error getting session:', error)
    throw new Error('Authentication error: ' + error.message)
  }
  
  if (!session?.access_token) {
    console.error('No session or access token available')
    throw new Error('Not authenticated. Please sign in.')
  }
  
  headers['Authorization'] = `Bearer ${session.access_token}`
  return headers
}

export async function generatePlan(
  sessionId: string,
  request: GeneratePlanRequest
): Promise<JobResponse> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_HOST}/generate-plan/${sessionId}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

export async function getPlanStatus(jobId: string): Promise<PlanStatusResponse> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_HOST}/plan/${jobId}`, {
    method: 'GET',
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

export async function generateBlog(
  sessionId: string,
  request: GenerateBlogRequest
): Promise<JobResponse> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_HOST}/generate-blog/${sessionId}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

export async function getBlogStatus(jobId: string): Promise<BlogStatusResponse> {
  const headers = await getAuthHeaders()
  const response = await fetch(`${API_HOST}/blog/${jobId}`, {
    method: 'GET',
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

