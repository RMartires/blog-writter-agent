"""
Background worker for processing plan generation jobs
"""
import time
import logging
import sys
import os
from threading import Thread
from typing import Optional

# Add parent directory to path to import agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.researcher import ResearchAgent
from agents.rag_manager import RAGManager
from agents.planner import PlannerAgent
from backend.job_manager import init_jobs_collection, get_processing_jobs, update_job_status
import config

logger = logging.getLogger(__name__)


class PlanGenerationWorker:
    """Background worker that processes plan generation jobs"""
    
    def __init__(self, poll_interval: int = 5):
        """
        Initialize the worker
        
        Args:
            poll_interval: Seconds to wait between polling for new jobs
        """
        self.poll_interval = poll_interval
        self.running = False
        self.thread: Optional[Thread] = None
        self.collection = None
        
    def start(self):
        """Start the worker thread"""
        if self.running:
            logger.warning("Worker is already running")
            return
        
        self.collection = init_jobs_collection()
        if self.collection is None:
            logger.error("Failed to initialize MongoDB collection. Worker cannot start.")
            return
        
        self.running = True
        self.thread = Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        logger.info("Plan generation worker started")
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        logger.info("Plan generation worker stopped")
    
    def _worker_loop(self):
        """Main worker loop that polls for jobs and processes them"""
        while self.running:
            try:
                # Get jobs with status "processing"
                jobs = get_processing_jobs(self.collection, limit=5)
                
                if jobs:
                    logger.info(f"Found {len(jobs)} jobs to process")
                
                for job in jobs:
                    if not self.running:
                        break
                    
                    job_id = job["job_id"]
                    keyword = job["keyword"]
                    session_id = job.get("session_id", job_id)
                    
                    logger.info(f"Processing job {job_id} for keyword: {keyword}")
                    
                    try:
                        # Process the job
                        plan = self._generate_plan(keyword, session_id)
                        
                        # Update job status to completed
                        update_job_status(
                            self.collection,
                            job_id,
                            status="completed",
                            plan=plan.model_dump() if plan else None
                        )
                        
                        logger.info(f"Job {job_id} completed successfully")
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Error processing job {job_id}: {error_msg}")
                        
                        # Update job status to failed
                        update_job_status(
                            self.collection,
                            job_id,
                            status="failed",
                            error=error_msg
                        )
                
                # Wait before polling again
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                time.sleep(self.poll_interval)
    
    def _generate_plan(self, keyword: str, session_id: str):
        """
        Generate a blog plan (reused from main.py logic)
        
        Args:
            keyword: Topic/keyword for plan generation
            session_id: Session ID for logging
            
        Returns:
            BlogPlan object
        """
        # Initialize agents with session ID for trace grouping
        researcher = ResearchAgent(config.TAVILY_API_KEY)
        rag_manager = RAGManager(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
        planner = PlannerAgent(
            config.OPENROUTER_API_KEY,
            config.OPENROUTER_MODEL,
            session_id=session_id
        )
        
        # Step 1: Research
        logger.info(f"[{session_id}] 🔍 Researching '{keyword}'...")
        research_data = researcher.search(
            keyword,
            max_results=5
        )
        
        if not research_data:
            raise ValueError("No research data found. Please try a different keyword.")
        
        logger.info(f"[{session_id}] ✓ Found {len(research_data)} relevant sources")
        
        # Step 2: Build RAG knowledge base
        logger.info(f"[{session_id}] 📚 Building knowledge base...")
        rag_manager.ingest_research(research_data)
        logger.info(f"[{session_id}] ✓ Knowledge base ready")
        
        # Step 3: Create research summary for planner
        research_summary = "\n".join([
            f"- {r['title']}: {r['content']}"
            for r in research_data
        ])
        
        # Step 4: Generate plan
        logger.info(f"[{session_id}] 📋 Planning blog structure...")
        plan = planner.create_plan(
            topic=keyword,
            target_keywords=[],
            research_summary=research_summary
        )
        
        logger.info(f"[{session_id}] ✓ Plan created: '{plan.title}' with {plan.get_section_count()} sections")
        
        return plan


# Global worker instance
_worker: Optional[PlanGenerationWorker] = None


def start_worker(poll_interval: int = 5):
    """Start the global worker instance"""
    global _worker
    if _worker is None:
        _worker = PlanGenerationWorker(poll_interval=poll_interval)
        _worker.start()
    return _worker


def stop_worker():
    """Stop the global worker instance"""
    global _worker
    if _worker:
        _worker.stop()
        _worker = None

