from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import sys
import os
import uuid

# Add parent directory to path to import agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.models import BlogPlan
from backend.job_manager import (
    init_jobs_collection, create_job, get_job, update_job_status, find_job_by_keyword,
    init_blog_jobs_collection, create_blog_job, get_blog_job, update_blog_job_status,
    find_blog_job_by_plan_job_id
)
from typing import Optional
from backend.worker import start_worker, stop_worker, start_blog_worker, stop_blog_worker
import config

app = FastAPI(title="AI Blog Writer API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MongoDB collections for jobs
jobs_collection = None
blog_jobs_collection = None


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    global jobs_collection, blog_jobs_collection
    jobs_collection = init_jobs_collection()
    blog_jobs_collection = init_blog_jobs_collection()
    if jobs_collection is None:
        print("Warning: Failed to initialize MongoDB. Plan job creation will fail.")
    else:
        # Start background worker for plan generation
        start_worker(poll_interval=5)
        print("Plan generation worker started")
    
    if blog_jobs_collection is None:
        print("Warning: Failed to initialize MongoDB. Blog job creation will fail.")
    else:
        # Start background worker for blog generation
        start_blog_worker(poll_interval=5)
        print("Blog generation worker started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    stop_worker()
    stop_blog_worker()
    print("Background workers stopped")


class GeneratePlanRequest(BaseModel):
    keyword: str = Field(..., description="Topic or keyword for blog post generation")


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class PlanStatusResponse(BaseModel):
    job_id: str
    status: str
    keyword: str
    created_at: str
    updated_at: str
    plan: Optional[dict] = None
    error: Optional[str] = None


class GenerateBlogRequest(BaseModel):
    plan: dict = Field(..., description="Blog plan object")
    plan_job_id: Optional[str] = Field(None, description="Optional plan job ID to retrieve research data from")


class BlogStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    updated_at: str
    blog: Optional[str] = None
    error: Optional[str] = None
    plan_job_id: Optional[str] = None


@app.post(
    "/generate-plan/{session_id}",
    response_model=JobResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def generate_plan(session_id: str, request: GeneratePlanRequest):
    """
    Create a job to generate a blog plan based on a keyword/topic.
    Returns immediately with job_id. Use GET /plan/{job_id} to check status.
    
    Args:
        session_id: Unique identifier for request tracking/logging
        request: Request body containing keyword parameter
        
    Returns:
        JobResponse with job_id and status
    """
    # Validate keyword
    keyword = request.keyword.strip()
    if not keyword:
        raise HTTPException(
            status_code=400,
            detail="Keyword parameter is required and cannot be empty"
        )
    
    # Validate API keys
    if not config.OPENROUTER_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENROUTER_API_KEY not found in environment variables"
        )
    if not config.TAVILY_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="TAVILY_API_KEY not found in environment variables"
        )
    
    # Check if MongoDB is initialized
    if jobs_collection is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection not available"
        )
    
    try:
        # Check if a completed job with the same keyword already exists
        existing_job = find_job_by_keyword(jobs_collection, keyword, status="completed")
        
        if existing_job:
            # Return existing job_id
            print(f"[{session_id}] ♻️  Reusing existing job {existing_job['job_id']} for keyword: {keyword}")
            return JobResponse(
                job_id=existing_job["job_id"],
                status=existing_job["status"],
                message="Found existing plan. Use GET /plan/{job_id} to retrieve it."
            )
        
        # No existing job found, create a new one
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create job in database with status "processing"
        success = create_job(jobs_collection, job_id, keyword, session_id=session_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to create job"
            )
        
        return JobResponse(
            job_id=job_id,
            status="processing",
            message="Job created successfully. Use GET /plan/{job_id} to check status."
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle all other errors
        error_msg = str(e)
        print(f"[{session_id}] ❌ Error creating job: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating job: {error_msg}"
        )


@app.get(
    "/plan/{job_id}",
    response_model=PlanStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
def get_plan_status(job_id: str):
    """
    Get the status and result of a plan generation job.
    
    Args:
        job_id: Job identifier returned from POST /generate-plan/{uuid}
        
    Returns:
        PlanStatusResponse with job status and plan (if completed)
    """
    if jobs_collection is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection not available"
        )
    
    job = get_job(jobs_collection, job_id)
    
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    from datetime import datetime as dt
    
    # Handle datetime serialization
    created_at = job["created_at"]
    updated_at = job["updated_at"]
    
    if isinstance(created_at, dt):
        created_at = created_at.isoformat()
    else:
        created_at = str(created_at)
    
    if isinstance(updated_at, dt):
        updated_at = updated_at.isoformat()
    else:
        updated_at = str(updated_at)
    
    return PlanStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        keyword=job["keyword"],
        created_at=created_at,
        updated_at=updated_at,
        plan=job.get("plan"),
        error=job.get("error")
    )


@app.post(
    "/generate-blog/{session_id}",
    response_model=JobResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def generate_blog(session_id: str, request: GenerateBlogRequest):
    """
    Create a job to generate a blog post from a plan.
    Returns immediately with job_id. Use GET /blog/{job_id} to check status.
    
    Args:
        session_id: Unique identifier for request tracking/logging
        request: Request body containing plan parameter
        
    Returns:
        JobResponse with job_id and status
    """
    # Validate plan
    if not request.plan:
        raise HTTPException(
            status_code=400,
            detail="Plan parameter is required"
        )
    
    # Validate API keys
    if not config.OPENROUTER_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENROUTER_API_KEY not found in environment variables"
        )
    if not config.TAVILY_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="TAVILY_API_KEY not found in environment variables"
        )
    
    # Check if MongoDB is initialized
    if blog_jobs_collection is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection not available"
        )
    
    try:
        # Validate plan structure by parsing it
        try:
            plan = BlogPlan(**request.plan)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plan structure: {str(e)}"
            )
        
        # If plan_job_id is provided, validate it exists and is completed
        if request.plan_job_id:
            plan_job = get_job(jobs_collection, request.plan_job_id)
            if plan_job is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Plan job {request.plan_job_id} not found"
                )
            if plan_job.get("status") != "completed":
                raise HTTPException(
                    status_code=400,
                    detail=f"Plan job {request.plan_job_id} is not completed (status: {plan_job.get('status')})"
                )
            
            # Check if a blog job already exists for this plan_job_id
            existing_blog_job = find_blog_job_by_plan_job_id(
                blog_jobs_collection,
                request.plan_job_id,
                status="completed"
            )
            
            if existing_blog_job:
                # Return existing job_id
                print(f"[{session_id}] ♻️  Reusing existing blog job {existing_blog_job['job_id']} for plan_job_id: {request.plan_job_id}")
                return JobResponse(
                    job_id=existing_blog_job["job_id"],
                    status=existing_blog_job["status"],
                    message="Found existing blog. Use GET /blog/{job_id} to retrieve it."
                )
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create job in database with status "processing"
        success = create_blog_job(
            blog_jobs_collection,
            job_id,
            request.plan,
            session_id=session_id,
            plan_job_id=request.plan_job_id
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to create blog job"
            )
        
        return JobResponse(
            job_id=job_id,
            status="processing",
            message="Blog generation job created successfully. Use GET /blog/{job_id} to check status."
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle all other errors
        error_msg = str(e)
        print(f"[{session_id}] ❌ Error creating blog job: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating blog job: {error_msg}"
        )


@app.get(
    "/blog/{job_id}",
    response_model=BlogStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
def get_blog_status(job_id: str):
    """
    Get the status and result of a blog generation job.
    
    Args:
        job_id: Job identifier returned from POST /generate-blog/{uuid}
        
    Returns:
        BlogStatusResponse with job status and blog content (if completed)
    """
    if blog_jobs_collection is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection not available"
        )
    
    job = get_blog_job(blog_jobs_collection, job_id)
    
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Blog job {job_id} not found"
        )
    
    from datetime import datetime as dt
    
    # Handle datetime serialization
    created_at = job["created_at"]
    updated_at = job["updated_at"]
    
    if isinstance(created_at, dt):
        created_at = created_at.isoformat()
    else:
        created_at = str(created_at)
    
    if isinstance(updated_at, dt):
        updated_at = updated_at.isoformat()
    else:
        updated_at = str(updated_at)
    
    return BlogStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        created_at=created_at,
        updated_at=updated_at,
        blog=job.get("blog"),
        error=job.get("error"),
        plan_job_id=job.get("plan_job_id")
    )


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

