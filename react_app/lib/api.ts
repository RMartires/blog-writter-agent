import { GeneratePlanRequest, JobResponse, PlanStatusResponse, GenerateBlogRequest, BlogStatusResponse } from '@/types/api'

const API_HOST = process.env.NEXT_PUBLIC_API_HOST || 'http://localhost:8000'

export async function generatePlan(
  sessionId: string,
  request: GeneratePlanRequest
): Promise<JobResponse> {
  const response = await fetch(`${API_HOST}/generate-plan/${sessionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

export async function getPlanStatus(jobId: string): Promise<PlanStatusResponse> {
  const response = await fetch(`${API_HOST}/plan/${jobId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
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
  const response = await fetch(`${API_HOST}/generate-blog/${sessionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

export async function getBlogStatus(jobId: string): Promise<BlogStatusResponse> {
  const response = await fetch(`${API_HOST}/blog/${jobId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

