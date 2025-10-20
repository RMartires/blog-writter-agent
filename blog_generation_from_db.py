#!/usr/bin/env python3
"""
Blog Generation from Database - Retrieve articles from MongoDB and generate blog posts
"""
import argparse
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.rag_manager import RAGManager
from agents.writer import WriterAgent
from agents.scorer import BlogScorer
from agents.planner import PlannerAgent
from agents.db_utils import init_mongodb, get_articles_by_query, get_articles_by_filters, get_article_stats
import config

# Load environment variables
load_dotenv()


def convert_articles_to_research_data(articles):
    """Convert ArticlePlan objects to research data format for RAG"""
    research_data = []
    
    for article in articles:
        # Create comprehensive content from article structure
        content_parts = []
        if article.intro:
            content_parts.append(f"Introduction: {article.intro}")
        
        for section in article.sections:
            content_parts.append(f"## {section.heading}")
            content_parts.append(section.text)
            
            for subsection in section.subsections:
                content_parts.append(f"### {subsection.heading}")
                content_parts.append(subsection.text)
        
        research_data.append({
            'title': article.title,
            'url': article.url,
            'content': '\n\n'.join(content_parts),
            'score': 1.0  # High quality due to detailed extraction
        })
    
    return research_data


def generate_blog_from_db(topic: str, 
                        query: str = None,
                        target_keywords: list = None,
                        min_word_count: int = None,
                        max_word_count: int = None,
                        min_section_count: int = None,
                        limit: int = None):
    """
    Generate a blog post using articles from MongoDB
    
    Args:
        topic: The blog post topic
        query: Original search query to filter articles (optional)
        target_keywords: Optional list of target keywords for SEO optimization
        min_word_count: Minimum word count filter for articles
        max_word_count: Maximum word count filter for articles
        min_section_count: Minimum section count filter for articles
        limit: Maximum number of articles to use
        
    Returns:
        Path to the generated blog post file
    """
    if target_keywords is None:
        target_keywords = []
    
    print(f"\n{'='*60}")
    print(f"AI Blog Writer - Database Generation")
    print(f"{'='*60}")
    print(f"Topic: {topic}")
    print(f"Model: {config.OPENROUTER_MODEL}")
    if query:
        print(f"Source Query: {query}")
    if target_keywords:
        keywords_str = ", ".join(target_keywords)
        print(f"Target Keywords: {keywords_str}")
    print(f"{'='*60}\n")
    
    # Initialize MongoDB
    collection = init_mongodb()
    if collection is None:
        print("❌ Failed to connect to MongoDB")
        return None
    
    # Retrieve articles from database
    print(f"🔍 Retrieving articles from database...")
    
    try:
        if query:
            # Get articles by specific query
            articles = get_articles_by_query(collection, query)
            print(f"   Found {len(articles)} articles for query: {query}")
        else:
            # Get articles with filters
            articles = get_articles_by_filters(
                collection,
                query=query,
                min_word_count=min_word_count,
                max_word_count=max_word_count,
                min_section_count=min_section_count,
                limit=limit
            )
            print(f"   Found {len(articles)} articles with filters")
        
        if not articles:
            print("❌ No articles found in database")
            print("   Try running researcher_data_dump.py first")
            return None
        
        print(f"✓ Retrieved {len(articles)} articles")
        
    except Exception as e:
        print(f"❌ Error retrieving articles: {e}")
        return None
    
    # Convert to research data format
    print(f"📚 Converting articles to research data format...")
    research_data = convert_articles_to_research_data(articles)
    print(f"✓ Converted {len(research_data)} articles")
    
    # Initialize agents
    try:
        rag_manager = RAGManager(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
        writer = WriterAgent(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
        planner = PlannerAgent(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
        scorer = BlogScorer(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
        print("✓ Agents initialized")
    except Exception as e:
        print(f"❌ Error initializing agents: {e}")
        return None
    
    # Step 1: Build RAG knowledge base
    print(f"\n📚 Step 1/6: Building knowledge base...")
    try:
        rag_manager.ingest_research(research_data)
        print("✓ Knowledge base ready")
    except Exception as e:
        print(f"❌ Error building knowledge base: {e}")
        return None
    
    # Step 2: Create blog plan
    print(f"\n📋 Step 2/6: Planning blog structure...")
    
    # Create research summary for planner
    research_summary = "\n".join([
        f"- {r['title']}: {r['content'][:500]}..." 
        for r in research_data
    ])
    
    try:
        plan = planner.create_plan(
            topic=topic,
            target_keywords=target_keywords,
            research_summary=research_summary
        )
        
        print(f"✓ Plan created: '{plan.title}'")
        print(f"  Sections ({len(plan.sections)}):")
        for i, section in enumerate(plan.sections, 1):
            print(f"    {i}. {section.heading}")
        
    except Exception as e:
        print(f"❌ Error creating plan: {e}")
        return None
    
    # Step 3: Generate introduction
    print(f"\n✍️  Step 3/6: Generating introduction...")
    
    intro_context = rag_manager.retrieve_context(topic, k=3)
    
    try:
        intro_content = writer.generate_intro(
            topic=topic,
            plan=plan,
            context_docs=intro_context,
            length_guidance=plan.intro_length_guidance
        )
        word_count = BlogScorer.count_words(intro_content)
        print(f"✓ Introduction complete ({word_count} words)")
    except Exception as e:
        print(f"❌ Error generating introduction: {e}")
        return None
    
    # Step 4: Generate sections
    print(f"\n✍️  Step 4/6: Generating sections...")
    
    section_contents = []
    
    for i, section in enumerate(plan.sections, 1):
        print(f"\n  📝 Section {i}/{len(plan.sections)}: {section.heading}")
        
        # Retrieve section-specific context
        section_query = f"{topic} {section.heading}"
        section_context = rag_manager.retrieve_context(section_query, k=3)
        
        try:
            section_content = writer.generate_section_with_subsections(
                section=section,
                topic=topic,
                context_docs=section_context,
                previous_sections=section_contents,
                rag_manager=rag_manager
            )
            word_count = BlogScorer.count_words(section_content)
            print(f"     ✓ Generated ({word_count} words)")
        except Exception as e:
            print(f"     ❌ Error generating section: {e}")
            return None
        
        section_contents.append(section_content)
    
    # Step 5: Stitch content together
    print(f"\n🔗 Step 5/6: Stitching content together...")
    
    final_blog_parts = [intro_content] + section_contents
    final_blog = "\n\n".join(final_blog_parts)
    
    print(f"✓ Blog assembled")
    
    # Step 6: Save output
    print(f"\n💾 Step 6/6: Saving output...")
    
    # Create output directory if it doesn't exist
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate filename
    safe_topic = topic.replace(' ', '_').replace('/', '_')[:30]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{output_dir}/blog_db_{safe_topic}_{timestamp}.md"
    
    # Calculate final metrics
    total_word_count = BlogScorer.count_words(final_blog)
    flesch_score = BlogScorer.calculate_flesch_score(final_blog)
    keyword_density = BlogScorer.calculate_keyword_density(final_blog, target_keywords)
    
    # Write blog post with sources and metadata
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# {plan.title}\n\n")
        f.write(final_blog)
        f.write("\n\n---\n\n")
        
        # Add metadata section
        f.write("## Metadata\n\n")
        f.write(f"- **Total Sections**: {len(section_contents)}\n")
        if target_keywords:
            keywords_str = ", ".join(target_keywords)
            f.write(f"- **Target Keywords**: {keywords_str}\n")
        f.write(f"- **Word Count**: {total_word_count}\n")
        f.write(f"- **Readability (Flesch)**: {flesch_score:.1f}\n")
        f.write(f"- **Keyword Density**: {keyword_density:.2f}%\n")
        f.write(f"- **Research Method**: Database Retrieval (MongoDB)\n")
        if query:
            f.write(f"- **Source Query**: {query}\n")
        f.write(f"- **Articles Used**: {len(articles)}\n")
        
        f.write("\n---\n\n## Sources\n\n")
        
        # Add source citations
        for r in research_data:
            title = r.get('title', 'Untitled')
            url = r.get('url', '#')
            f.write(f"- [{title}]({url})\n")
    
    print(f"✓ Saved to: {filename}")
    
    # Print statistics
    print(f"\n{'='*60}")
    print(f"📊 Final Statistics:")
    print(f"   - Word count: {total_word_count}")
    print(f"   - Number of sections: {len(section_contents)}")
    print(f"   - Sources used: {len(research_data)}")
    print(f"   - Flesch reading ease: {flesch_score:.1f}")
    print(f"   - Keyword density: {keyword_density:.2f}%")
    print(f"   - Research method: Database Retrieval")
    print(f"{'='*60}\n")
    
    return filename


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="Generate blog from MongoDB articles")
    parser.add_argument("--topic", "-t", required=True, help="Blog topic")
    parser.add_argument("--query", "-q", help="Source query to filter articles")
    parser.add_argument("--keywords", "-k", nargs="+", help="Target keywords for SEO")
    parser.add_argument("--min-words", type=int, help="Minimum word count filter")
    parser.add_argument("--max-words", type=int, help="Maximum word count filter")
    parser.add_argument("--min-sections", type=int, help="Minimum section count filter")
    parser.add_argument("--limit", type=int, help="Maximum number of articles to use")
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
    
    # Generate blog
    filename = generate_blog_from_db(
        topic=args.topic,
        query=args.query,
        target_keywords=args.keywords,
        min_word_count=args.min_words,
        max_word_count=args.max_words,
        min_section_count=args.min_sections,
        limit=args.limit
    )
    
    if filename:
        print(f"✅ Blog generated successfully: {filename}")
    else:
        print("❌ Blog generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
