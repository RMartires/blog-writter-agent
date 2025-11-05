from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import sys
import os

# Add parent directory to path to import agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.researcher import ResearchAgent
from agents.rag_manager import RAGManager
from agents.planner import PlannerAgent
from agents.models import BlogPlan
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


class GeneratePlanRequest(BaseModel):
    keyword: str = Field(..., description="Topic or keyword for blog post generation")


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


@app.post(
    "/generate-plan/{uuid}",
    response_model=BlogPlan,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def generate_plan(uuid: str, request: GeneratePlanRequest):
    """
    Generate a blog plan based on a keyword/topic.
    
    Args:
        uuid: Unique identifier for request tracking/logging
        request: Request body containing keyword parameter
        
    Returns:
        BlogPlan object with title, intro, and sections structure
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
    
    try:
        # Initialize agents with session ID for trace grouping
        researcher = ResearchAgent(config.TAVILY_API_KEY)
        rag_manager = RAGManager(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
        planner = PlannerAgent(
            config.OPENROUTER_API_KEY,
            config.OPENROUTER_MODEL,
            session_id=uuid
        )
        
        # Step 1: Research
        print(f"[{uuid}] 🔍 Researching '{keyword}'...")
        research_data = researcher.search(
            keyword,
            max_results=5
        )
        
        if not research_data:
            raise HTTPException(
                status_code=500,
                detail="No research data found. Please try a different keyword."
            )
        
        print(f"[{uuid}] ✓ Found {len(research_data)} relevant sources")
        
        # Step 2: Build RAG knowledge base
        print(f"[{uuid}] 📚 Building knowledge base...")
        rag_manager.ingest_research(research_data)
        print(f"[{uuid}] ✓ Knowledge base ready")
        
        # Step 3: Create research summary for planner
        research_summary = "\n".join([
            f"- {r['title']}: {r['content']}"
            for r in research_data
        ])
        
        # Step 4: Generate plan
        print(f"[{uuid}] 📋 Planning blog structure...")
        plan = planner.create_plan(
            topic=keyword,
            target_keywords=[],
            research_summary=research_summary
        )
        
        print(f"[{uuid}] ✓ Plan created: '{plan.title}' with {plan.get_section_count()} sections")
        
        # Return plan as JSON (Pydantic model automatically serializes)
        return plan
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        # Handle all other errors
        error_msg = str(e)
        print(f"[{uuid}] ❌ Error: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating plan: {error_msg}"
        )


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

