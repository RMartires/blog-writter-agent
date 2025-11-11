"""
Job management utilities for plan generation jobs
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure
import config

logger = logging.getLogger(__name__)


def init_jobs_collection() -> Optional[Collection]:
    """Initialize MongoDB connection and return plan jobs collection"""
    try:
        client = MongoClient(config.MONGO_DB_URI)
        # Test connection
        client.admin.command('ping')
        
        db = client[config.MONGO_DB_NAME]
        collection = db[config.MONGO_COLLECTION_PLAN_JOBS]
        
        # Create indexes for better performance
        collection.create_index("job_id", unique=True)
        collection.create_index("status")
        collection.create_index("created_at")
        collection.create_index("keyword")  # For keyword-based searches
        collection.create_index("user_id")  # For user-based queries
        
        logger.info(f"Connected to MongoDB: {config.MONGO_DB_NAME}.{config.MONGO_COLLECTION_PLAN_JOBS}")
        return collection
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None
    except Exception as e:
        logger.error(f"Error initializing MongoDB: {e}")
        return None


def init_blog_jobs_collection() -> Optional[Collection]:
    """Initialize MongoDB connection and return blog generation jobs collection"""
    try:
        client = MongoClient(config.MONGO_DB_URI)
        # Test connection
        client.admin.command('ping')
        
        db = client[config.MONGO_DB_NAME]
        collection = db[config.MONGO_COLLECTION_BLOG_JOBS]
        
        # Create indexes for better performance
        collection.create_index("job_id", unique=True)
        collection.create_index("status")
        collection.create_index("created_at")
        collection.create_index("user_id")  # For user-based queries
        
        logger.info(f"Connected to MongoDB: {config.MONGO_DB_NAME}.{config.MONGO_COLLECTION_BLOG_JOBS}")
        return collection
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None
    except Exception as e:
        logger.error(f"Error initializing MongoDB: {e}")
        return None


def create_job(collection: Collection, job_id: str, keyword: str, user_id: str, session_id: str = None) -> bool:
    """Create a new plan generation job"""
    try:
        doc = {
            "job_id": job_id,
            "keyword": keyword,
            "user_id": user_id,
            "status": "processing",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "session_id": session_id,
            "plan": None,
            "error": None
        }
        
        result = collection.insert_one(doc)
        logger.info(f"Created job {job_id} for keyword: {keyword}, user_id: {user_id}")
        return result.inserted_id is not None
        
    except Exception as e:
        logger.error(f"Error creating job {job_id}: {e}")
        return False


def get_job(collection: Collection, job_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a job by job_id, optionally filtered by user_id"""
    try:
        query = {"job_id": job_id}
        if user_id:
            query["user_id"] = user_id
        
        job = collection.find_one(query)
        if job:
            # Convert ObjectId to string for JSON serialization
            job["_id"] = str(job["_id"])
        return job
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        return None


def update_job_status(
    collection: Collection,
    job_id: str,
    status: str,
    plan: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    research_data: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """Update job status and optionally plan, error, or research_data"""
    try:
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        if plan is not None:
            update_data["plan"] = plan
        if error is not None:
            update_data["error"] = error
        if research_data is not None:
            update_data["research_data"] = research_data
        
        result = collection.update_one(
            {"job_id": job_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated job {job_id} to status: {status}")
            return True
        else:
            logger.warning(f"No job found or no changes for job {job_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {e}")
        return False


def get_processing_jobs(collection: Collection, limit: int = 10) -> list:
    """Get jobs with status 'processing'"""
    try:
        jobs = list(collection.find({"status": "processing"}).sort("created_at", 1).limit(limit))
        return jobs
    except Exception as e:
        logger.error(f"Error getting processing jobs: {e}")
        return []


def find_job_by_keyword(collection: Collection, keyword: str, user_id: str, status: str = "completed") -> Optional[Dict[str, Any]]:
    """
    Find an existing job by keyword (case-insensitive) for a specific user.
    Prefer completed jobs, but can search for any status.
    
    Args:
        collection: MongoDB collection
        keyword: Keyword to search for
        user_id: User ID to filter by
        status: Status to filter by (default: "completed")
        
    Returns:
        Job document if found, None otherwise
    """
    try:
        # Case-insensitive search for keyword, filtered by user_id
        # Find the most recent completed job with matching keyword and user_id
        job = collection.find_one(
            {
                "keyword": {"$regex": f"^{keyword}$", "$options": "i"},  # Case-insensitive exact match
                "status": status,
                "user_id": user_id
            },
            sort=[("created_at", -1)]  # Get most recent first
        )
        
        if job:
            job["_id"] = str(job["_id"])
            logger.info(f"Found existing job {job['job_id']} for keyword: {keyword}, user_id: {user_id}")
            return job
        
        return None
    except Exception as e:
        logger.error(f"Error finding job by keyword '{keyword}': {e}")
        return None


# Blog generation job functions

def create_blog_job(collection: Collection, job_id: str, plan: dict, user_id: str, session_id: str = None, plan_job_id: Optional[str] = None) -> bool:
    """Create a new blog generation job"""
    try:
        doc = {
            "job_id": job_id,
            "plan": plan,
            "user_id": user_id,
            "status": "processing",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "session_id": session_id,
            "blog": None,
            "sections": [],
            "error": None
        }
        
        if plan_job_id is not None:
            doc["plan_job_id"] = plan_job_id
        
        result = collection.insert_one(doc)
        logger.info(f"Created blog job {job_id}, user_id: {user_id}")
        return result.inserted_id is not None
        
    except Exception as e:
        logger.error(f"Error creating blog job {job_id}: {e}")
        return False


def get_blog_job(collection: Collection, job_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a blog job by job_id, optionally filtered by user_id"""
    try:
        query = {"job_id": job_id}
        if user_id:
            query["user_id"] = user_id
        
        job = collection.find_one(query)
        if job:
            # Convert ObjectId to string for JSON serialization
            job["_id"] = str(job["_id"])
        return job
    except Exception as e:
        logger.error(f"Error getting blog job {job_id}: {e}")
        return None


def update_blog_job_status(
    collection: Collection,
    job_id: str,
    status: str,
    blog: Optional[str] = None,
    error: Optional[str] = None,
    sections: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """Update blog job status and optionally blog content, sections, or error"""
    try:
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        if blog is not None:
            update_data["blog"] = blog
        if error is not None:
            update_data["error"] = error
        if sections is not None:
            update_data["sections"] = sections
        
        result = collection.update_one(
            {"job_id": job_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated blog job {job_id} to status: {status}")
            return True
        else:
            logger.warning(f"No blog job found or no changes for job {job_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating blog job {job_id}: {e}")
        return False


def append_blog_job_section(
    collection: Collection,
    job_id: str,
    section: Dict[str, Any]
) -> bool:
    """Append a single section entry to a blog job"""
    try:
        result = collection.update_one(
            {"job_id": job_id},
            {
                "$push": {"sections": section},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        if result.modified_count > 0:
            logger.info(f"Appended section to blog job {job_id}")
            return True
        else:
            logger.warning(f"No blog job found to append section for job {job_id}")
            return False

    except Exception as e:
        logger.error(f"Error appending section to blog job {job_id}: {e}")
        return False


def get_processing_blog_jobs(collection: Collection, limit: int = 10) -> list:
    """Get blog jobs with status 'processing'"""
    try:
        jobs = list(collection.find({"status": "processing"}).sort("created_at", 1).limit(limit))
        return jobs
    except Exception as e:
        logger.error(f"Error getting processing blog jobs: {e}")
        return []


def find_blog_job_by_plan_job_id(collection: Collection, plan_job_id: str, user_id: str, status: str = "completed") -> Optional[Dict[str, Any]]:
    """
    Find an existing blog job by plan_job_id for a specific user.
    Prefer completed jobs, but can search for any status.
    
    Args:
        collection: MongoDB collection
        plan_job_id: Plan job ID to search for
        user_id: User ID to filter by
        status: Status to filter by (default: "completed")
        
    Returns:
        Blog job document if found, None otherwise
    """
    try:
        # Find the most recent completed blog job with matching plan_job_id and user_id
        job = collection.find_one(
            {
                "plan_job_id": plan_job_id,
                "user_id": user_id,
                "status": status
            },
            sort=[("created_at", -1)]  # Get most recent first
        )
        
        if job:
            job["_id"] = str(job["_id"])
            logger.info(f"Found existing blog job {job['job_id']} for plan_job_id: {plan_job_id}, user_id: {user_id}")
            return job
        
        return None
    except Exception as e:
        logger.error(f"Error finding blog job by plan_job_id '{plan_job_id}': {e}")
        return None

