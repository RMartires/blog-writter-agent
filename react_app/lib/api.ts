import { GeneratePlanRequest, JobResponse, PlanStatusResponse } from '@/types/api'

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

