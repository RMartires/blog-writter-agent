#!/usr/bin/env python3
"""
Researcher Data Dump - Extract articles and save to MongoDB
"""
import asyncio
import argparse
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.researcher_v2 import ResearchAgentV2
from agents.db_utils import init_mongodb, save_article, get_article_stats, article_exists
import config

# Load environment variables
load_dotenv()


async def extract_and_save_articles(query: str, max_articles: int = 5, force_update: bool = False):
    """
    Extract articles and save to MongoDB
    
    Args:
        query: Search query
        max_articles: Maximum number of articles to extract
        force_update: Whether to update existing articles
    """
    print("=" * 60)
    print("Researcher Data Dump - Article Extraction")
    print("=" * 60)
    print(f"Query: {query}")
    print(f"Max Articles: {max_articles}")
    print(f"Force Update: {force_update}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Initialize MongoDB
    collection = init_mongodb()
    if collection is None:
        print("❌ Failed to connect to MongoDB")
        return False
    
    # Initialize researcher
    try:
        researcher = ResearchAgentV2(
            api_key=config.OPENROUTER_API_KEY,
            playwright_path=config.PLAYWRIGHT_BROWSERS_PATH
        )
        print("✓ ResearchAgentV2 initialized")
    except Exception as e:
        print(f"❌ Error initializing ResearchAgentV2: {e}")
        return False
    
    # Extract articles
    print(f"\n🔍 Extracting articles for query: {query}")
    try:
        articles = await researcher.search_and_extract_articles(
            query=query,
            max_articles=max_articles
        )
        
        if not articles:
            print("❌ No articles extracted")
            return False
        
        print(f"✓ Extracted {len(articles)} articles")
        
    except Exception as e:
        print(f"❌ Error extracting articles: {e}")
        return False
    
    # Save articles to MongoDB
    print(f"\n💾 Saving articles to MongoDB...")
    saved_count = 0
    updated_count = 0
    failed_count = 0
    
    for i, article in enumerate(articles, 1):
        print(f"\n📄 Processing article {i}/{len(articles)}: {article.title}")
        print(f"   URL: {article.url}")
        
        # Check if article already exists
        exists = article_exists(collection, article.url)
        if exists and not force_update:
            print(f"   ⚠️  Article already exists, skipping (use --force-update to override)")
            continue
        
        # Save article
        try:
            success = save_article(collection, query, article, "completed")
            if success:
                if exists:
                    updated_count += 1
                    print(f"   ✓ Updated in database")
                else:
                    saved_count += 1
                    print(f"   ✓ Saved to database")
            else:
                failed_count += 1
                print(f"   ❌ Failed to save")
                
        except Exception as e:
            failed_count += 1
            print(f"   ❌ Error saving article: {e}")
    
    # Print summary
    print(f"\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    print(f"Total articles processed: {len(articles)}")
    print(f"New articles saved: {saved_count}")
    print(f"Articles updated: {updated_count}")
    print(f"Failed to save: {failed_count}")
    
    # Get database stats
    stats = get_article_stats(collection)
    if stats:
        print(f"\n📈 Database Statistics:")
        print(f"   Total articles in DB: {stats.get('total_articles', 0)}")
        print(f"   Completed articles: {stats.get('completed_articles', 0)}")
        print(f"   Failed articles: {stats.get('failed_articles', 0)}")
        print(f"   Unique queries: {stats.get('unique_queries', 0)}")
        print(f"   Average word count: {stats.get('avg_word_count', 0)}")
    
    print("=" * 60)
    
    return saved_count + updated_count > 0


async def batch_extract_queries(queries: list, max_articles: int = 5, force_update: bool = False):
    """
    Extract articles for multiple queries
    
    Args:
        queries: List of search queries
        max_articles: Maximum articles per query
        force_update: Whether to update existing articles
    """
    print("=" * 60)
    print("Batch Article Extraction")
    print("=" * 60)
    print(f"Queries: {len(queries)}")
    print(f"Max Articles per Query: {max_articles}")
    print("=" * 60)
    
    total_saved = 0
    total_failed = 0
    
    for i, query in enumerate(queries, 1):
        print(f"\n🔍 Processing query {i}/{len(queries)}: {query}")
        
        try:
            success = await extract_and_save_articles(query, max_articles, force_update)
            if success:
                total_saved += 1
            else:
                total_failed += 1
        except Exception as e:
            print(f"❌ Error processing query {query}: {e}")
            total_failed += 1
        
        # Add delay between queries to avoid rate limiting
        if i < len(queries):
            print("⏸️  Waiting 5 seconds before next query...")
            await asyncio.sleep(5)
    
    print(f"\n" + "=" * 60)
    print("📊 Batch Summary")
    print("=" * 60)
    print(f"Total queries processed: {len(queries)}")
    print(f"Successful queries: {total_saved}")
    print(f"Failed queries: {total_failed}")
    print("=" * 60)


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="Extract articles and save to MongoDB")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--max-articles", "-m", type=int, default=5, help="Maximum articles to extract")
    parser.add_argument("--force-update", "-f", action="store_true", help="Update existing articles")
    parser.add_argument("--batch", "-b", nargs="+", help="Batch process multiple queries")
    parser.add_argument("--stats", "-s", action="store_true", help="Show database statistics only")
    
    args = parser.parse_args()
    
    # Check API key
    if not config.OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY not found in environment variables")
        sys.exit(1)
    
    # Show stats only
    if args.stats:
        collection = init_mongodb()
        if collection is not None:
            stats = get_article_stats(collection)
            print("📈 Database Statistics:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
        return
    
    # Batch processing
    if args.batch:
        asyncio.run(batch_extract_queries(args.batch, args.max_articles, args.force_update))
    else:
        # Single query processing
        asyncio.run(extract_and_save_articles(args.query, args.max_articles, args.force_update))


if __name__ == "__main__":
    main()
