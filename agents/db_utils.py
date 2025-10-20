"""
Database utilities for MongoDB operations
"""
import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, DuplicateKeyError

from .models import ArticlePlan, ArticleDocument
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_mongodb() -> Optional[Collection]:
    """Initialize MongoDB connection and return articles collection"""
    try:
        client = MongoClient(config.MONGO_DB_URI)
        # Test connection
        client.admin.command('ping')
        
        db = client[config.MONGO_DB_NAME]
        collection = db[config.MONGO_COLLECTION_ARTICLES]
        
        # Create indexes for better performance
        collection.create_index("query")
        collection.create_index("article.url", unique=True)
        collection.create_index("timestamp")
        collection.create_index("status")
        
        logger.info(f"Connected to MongoDB: {config.MONGO_DB_NAME}.{config.MONGO_COLLECTION_ARTICLES}")
        return collection
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None
    except Exception as e:
        logger.error(f"Error initializing MongoDB: {e}")
        return None


def save_article(collection: Collection, query: str, article: ArticlePlan, status: str = "completed") -> bool:
    """Save an article to MongoDB"""
    try:
        # Calculate word count
        word_count = 0
        if article.intro:
            word_count += len(article.intro.split())
        
        for section in article.sections:
            word_count += len(section.text.split())
            for subsection in section.subsections:
                word_count += len(subsection.text.split())
        
        # Create document
        doc = {
            "query": query,
            "timestamp": datetime.utcnow(),
            "article": article.model_dump(),
            "status": status,
            "word_count": word_count,
            "section_count": len(article.sections)
        }
        
        # Check if article already exists
        existing = collection.find_one({"article.url": article.url})
        if existing:
            # Update existing document
            result = collection.update_one(
                {"article.url": article.url},
                {"$set": doc}
            )
            logger.info(f"Updated existing article: {article.title}")
        else:
            # Insert new document
            result = collection.insert_one(doc)
            logger.info(f"Inserted new article: {article.title}")
        
        return True
        
    except DuplicateKeyError:
        logger.warning(f"Article already exists: {article.url}")
        return False
    except Exception as e:
        logger.error(f"Error saving article {article.title}: {e}")
        return False


def get_articles_by_query(collection: Collection, query: str, status: str = "completed") -> List[ArticlePlan]:
    """Get articles by search query"""
    try:
        cursor = collection.find({"query": query, "status": status})
        articles = []
        
        for doc in cursor:
            try:
                article_plan = ArticlePlan.model_validate(doc["article"])
                articles.append(article_plan)
            except Exception as e:
                logger.warning(f"Error parsing article from DB: {e}")
                continue
        
        logger.info(f"Retrieved {len(articles)} articles for query: {query}")
        return articles
        
    except Exception as e:
        logger.error(f"Error retrieving articles for query {query}: {e}")
        return []


def get_recent_articles(collection: Collection, limit: int = 10, status: str = "completed") -> List[ArticlePlan]:
    """Get recent articles"""
    try:
        cursor = collection.find({"status": status}).sort("timestamp", -1).limit(limit)
        articles = []
        
        for doc in cursor:
            try:
                article_plan = ArticlePlan.model_validate(doc["article"])
                articles.append(article_plan)
            except Exception as e:
                logger.warning(f"Error parsing article from DB: {e}")
                continue
        
        logger.info(f"Retrieved {len(articles)} recent articles")
        return articles
        
    except Exception as e:
        logger.error(f"Error retrieving recent articles: {e}")
        return []


def get_articles_by_filters(collection: Collection, 
                          query: Optional[str] = None,
                          min_word_count: Optional[int] = None,
                          max_word_count: Optional[int] = None,
                          min_section_count: Optional[int] = None,
                          status: str = "completed",
                          limit: Optional[int] = None) -> List[ArticlePlan]:
    """Get articles with various filters"""
    try:
        # Build filter
        filter_dict = {"status": status}
        
        if query:
            filter_dict["query"] = query
        
        if min_word_count is not None:
            filter_dict["word_count"] = {"$gte": min_word_count}
        
        if max_word_count is not None:
            if "word_count" in filter_dict:
                filter_dict["word_count"]["$lte"] = max_word_count
            else:
                filter_dict["word_count"] = {"$lte": max_word_count}
        
        if min_section_count is not None:
            filter_dict["section_count"] = {"$gte": min_section_count}
        
        # Execute query
        cursor = collection.find(filter_dict).sort("timestamp", -1)
        if limit:
            cursor = cursor.limit(limit)
        
        articles = []
        for doc in cursor:
            try:
                article_plan = ArticlePlan.model_validate(doc["article"])
                articles.append(article_plan)
            except Exception as e:
                logger.warning(f"Error parsing article from DB: {e}")
                continue
        
        logger.info(f"Retrieved {len(articles)} articles with filters")
        return articles
        
    except Exception as e:
        logger.error(f"Error retrieving articles with filters: {e}")
        return []


def article_exists(collection: Collection, url: str) -> bool:
    """Check if article exists in database"""
    try:
        result = collection.find_one({"article.url": url})
        return result is not None
    except Exception as e:
        logger.error(f"Error checking if article exists: {e}")
        return False


def get_article_stats(collection: Collection) -> Dict[str, Any]:
    """Get statistics about articles in database"""
    try:
        total_articles = collection.count_documents({})
        completed_articles = collection.count_documents({"status": "completed"})
        failed_articles = collection.count_documents({"status": "failed"})
        
        # Get unique queries
        unique_queries = collection.distinct("query")
        
        # Get average word count
        pipeline = [
            {"$match": {"status": "completed", "word_count": {"$exists": True}}},
            {"$group": {"_id": None, "avg_word_count": {"$avg": "$word_count"}}}
        ]
        avg_word_result = list(collection.aggregate(pipeline))
        avg_word_count = avg_word_result[0]["avg_word_count"] if avg_word_result else 0
        
        return {
            "total_articles": total_articles,
            "completed_articles": completed_articles,
            "failed_articles": failed_articles,
            "unique_queries": len(unique_queries),
            "avg_word_count": round(avg_word_count, 2)
        }
        
    except Exception as e:
        logger.error(f"Error getting article stats: {e}")
        return {}


def delete_articles_by_query(collection: Collection, query: str) -> int:
    """Delete all articles for a specific query"""
    try:
        result = collection.delete_many({"query": query})
        logger.info(f"Deleted {result.deleted_count} articles for query: {query}")
        return result.deleted_count
    except Exception as e:
        logger.error(f"Error deleting articles for query {query}: {e}")
        return 0


def update_article_status(collection: Collection, url: str, status: str) -> bool:
    """Update article status"""
    try:
        result = collection.update_one(
            {"article.url": url},
            {"$set": {"status": status}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating article status: {e}")
        return False
