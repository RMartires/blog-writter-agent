"""
Background worker for processing plan generation jobs
"""
import time
import logging
import sys
import os
from threading import Thread
from typing import Optional, List, Dict, Any

# Add parent directory to path to import agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.researcher import ResearchAgent
from agents.rag_manager import RAGManager
from agents.planner import PlannerAgent
from agents.writer import WriterAgent
from agents.models import BlogPlan
from backend.job_manager import (
    init_jobs_collection, get_processing_jobs, update_job_status, get_job,
    init_blog_jobs_collection, get_processing_blog_jobs, update_blog_job_status
)
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
                        plan, research_data = self._generate_plan(keyword, session_id)
                        
                        # Update job status to completed with plan and research_data
                        update_job_status(
                            self.collection,
                            job_id,
                            status="completed",
                            plan=plan.model_dump() if plan else None,
                            research_data=research_data
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
            Tuple of (BlogPlan object, research_data list)
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
        
        return plan, research_data


class BlogGenerationWorker:
    """Background worker that processes blog generation jobs"""
    
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
        self.plan_jobs_collection = None
        
    def start(self):
        """Start the worker thread"""
        if self.running:
            logger.warning("Blog worker is already running")
            return
        
        self.collection = init_blog_jobs_collection()
        self.plan_jobs_collection = init_jobs_collection()
        if self.collection is None:
            logger.error("Failed to initialize MongoDB collection. Blog worker cannot start.")
            return
        
        self.running = True
        self.thread = Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        logger.info("Blog generation worker started")
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        logger.info("Blog generation worker stopped")
    
    def _worker_loop(self):
        """Main worker loop that polls for jobs and processes them"""
        while self.running:
            try:
                # Get jobs with status "processing"
                jobs = get_processing_blog_jobs(self.collection, limit=5)
                
                if jobs:
                    logger.info(f"Found {len(jobs)} blog jobs to process")
                
                for job in jobs:
                    if not self.running:
                        break
                    
                    job_id = job["job_id"]
                    plan_dict = job["plan"]
                    session_id = job.get("session_id", job_id)
                    plan_job_id = job.get("plan_job_id")
                    
                    logger.info(f"Processing blog job {job_id}")
                    
                    try:
                        # Parse plan from dict
                        plan = BlogPlan(**plan_dict)
                        
                        # Try to retrieve research_data from plan_job_id if available
                        research_data = None
                        if plan_job_id and self.plan_jobs_collection is not None:
                            logger.info(f"[{session_id}] Looking up research data from plan job {plan_job_id}")
                            plan_job = get_job(self.plan_jobs_collection, plan_job_id)
                            if plan_job is not None and plan_job.get("status") == "completed":
                                research_data = plan_job.get("research_data")
                                if research_data:
                                    logger.info(f"[{session_id}] ✓ Found research data from plan job ({len(research_data)} sources)")
                                else:
                                    logger.warning(f"[{session_id}] Plan job {plan_job_id} found but no research_data available")
                            else:
                                logger.warning(f"[{session_id}] Plan job {plan_job_id} not found or not completed")
                        
                        # Process the job
                        blog_content = self._generate_blog(plan, session_id, research_data)
                        
                        # Update job status to completed
                        update_blog_job_status(
                            self.collection,
                            job_id,
                            status="completed",
                            blog=blog_content
                        )
                        
                        logger.info(f"Blog job {job_id} completed successfully")
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Error processing blog job {job_id}: {error_msg}")
                        
                        # Update job status to failed
                        update_blog_job_status(
                            self.collection,
                            job_id,
                            status="failed",
                            error=error_msg
                        )
                
                # Wait before polling again
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in blog worker loop: {e}")
                time.sleep(self.poll_interval)
    
    def _generate_blog(self, plan: BlogPlan, session_id: str, research_data: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Generate a blog post from a plan
        
        Args:
            plan: BlogPlan object
            session_id: Session ID for logging
            research_data: Optional pre-researched data to reuse (skips research step if provided)
            
        Returns:
            Generated blog content as markdown string
        """
        # Extract topic from plan title
        topic = plan.title
        
        # Initialize agents with session ID for trace grouping
        rag_manager = RAGManager(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
        writer = WriterAgent(
            config.OPENROUTER_API_KEY,
            config.OPENROUTER_MODEL,
            session_id=session_id
        )
        
        # Step 1: Research (or reuse existing research_data)
        if research_data is None:
            logger.info(f"[{session_id}] 🔍 Researching '{topic}'...")
            researcher = ResearchAgent(config.TAVILY_API_KEY)
            research_data = researcher.search(
                topic,
                max_results=5
            )
            
            if not research_data:
                raise ValueError("No research data found. Please try a different topic.")
            
            logger.info(f"[{session_id}] ✓ Found {len(research_data)} relevant sources")
        else:
            logger.info(f"[{session_id}] ♻️  Reusing research data ({len(research_data)} sources)")
        
        # Step 2: Build RAG knowledge base
        logger.info(f"[{session_id}] 📚 Building knowledge base...")
        rag_manager.ingest_research(research_data)
        logger.info(f"[{session_id}] ✓ Knowledge base ready")
        
        # Step 3: Generate introduction
        logger.info(f"[{session_id}] ✍️ Generating introduction...")
        intro_context = rag_manager.retrieve_context(topic, k=3)
        
        intro_content = writer.generate_intro(
            topic=topic,
            plan=plan,
            context_docs=intro_context,
            length_guidance=plan.intro_length_guidance
        )
        logger.info(f"[{session_id}] ✓ Introduction complete")
        
        # Step 4: Generate sections
        logger.info(f"[{session_id}] ✍️ Generating sections...")
        section_contents = []
        
        for i, section in enumerate(plan.sections, 1):
            logger.info(f"[{session_id}] 📝 Section {i}/{len(plan.sections)}: {section.heading}")
            
            # Retrieve section-specific context
            section_query = f"{topic} {section.heading}"
            section_context = rag_manager.retrieve_context(section_query, k=3)
            
            # Generate section (with or without subsections)
            section_content = writer.generate_section_with_subsections(
                section=section,
                topic=topic,
                context_docs=section_context,
                previous_sections=section_contents,
                rag_manager=rag_manager
            )
            
            section_contents.append(section_content)
            logger.info(f"[{session_id}] ✓ Section {i} complete")
        
        # Step 5: Combine all content
        logger.info(f"[{session_id}] 🔗 Stitching content together...")
        
        final_blog_parts = []
        final_blog_parts.append(intro_content)
        final_blog_parts.extend(section_contents)
        
        final_blog = "\n\n".join(final_blog_parts)
        
        # Add title at the top
        final_blog = f"# {plan.title}\n\n{final_blog}"
        
        logger.info(f"[{session_id}] ✓ Blog generation complete")
        
        return final_blog


# Global worker instances
_worker: Optional[PlanGenerationWorker] = None
_blog_worker: Optional[BlogGenerationWorker] = None


def start_worker(poll_interval: int = 5):
    """Start the global plan generation worker instance"""
    global _worker
    if _worker is None:
        _worker = PlanGenerationWorker(poll_interval=poll_interval)
        _worker.start()
    return _worker


def stop_worker():
    """Stop the global plan generation worker instance"""
    global _worker
    if _worker:
        _worker.stop()
        _worker = None


def start_blog_worker(poll_interval: int = 5):
    """Start the global blog generation worker instance"""
    global _blog_worker
    if _blog_worker is None:
        _blog_worker = BlogGenerationWorker(poll_interval=poll_interval)
        _blog_worker.start()
    return _blog_worker


def stop_blog_worker():
    """Stop the global blog generation worker instance"""
    global _blog_worker
    if _blog_worker:
        _blog_worker.stop()
        _blog_worker = None

