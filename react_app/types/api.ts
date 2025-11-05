// API Response Types

export enum JobStatus {
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

export interface GeneratePlanRequest {
  keyword: string
}

export interface JobResponse {
  job_id: string
  status: string
  message: string
}

export interface PlanStatusResponse {
  job_id: string
  status: JobStatus
  keyword: string
  created_at: string
  updated_at: string
  plan: BlogPlan | null
  error: string | null
}

export interface BlogPlan {
  title: string
  intro: string | null
  intro_length_guidance: string
  sections: BlogSection[]
}

export interface BlogSection {
  heading: string
  description: string | null
  subsections: SubSection[]
}

export interface SubSection {
  heading: string
  description: string | null
}

