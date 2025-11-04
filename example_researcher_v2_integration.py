#!/usr/bin/env python3
"""
Example integration of researcher_v2 with the existing blog generation workflow
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.researcher_v2 import ResearchAgentV2
from agents.rag_manager import RAGManager
from agents.writer import WriterAgent
from agents.scorer import BlogScorer
from agents.planner import PlannerAgent
import config


async def generate_blog_with_researcher_v2(topic: str, target_keywords: list = None):
    """
    Generate a blog post using researcher_v2 for enhanced content extraction
    
    Args:
        topic: The blog post topic
        target_keywords: Optional list of target keywords for SEO optimization
        
    Returns:
        Path to the generated blog post file
    """
    if target_keywords is None:
        target_keywords = []
    
    print(f"\n{'='*60}")
    print(f"AI Blog Writer with Enhanced Research (Researcher V2)")
    print(f"{'='*60}")
    print(f"Topic: {topic}")
    print(f"Model: {config.OPENROUTER_MODEL}")
    if target_keywords:
        keywords_str = ", ".join(target_keywords)
        print(f"Target Keywords: {keywords_str}")
    print(f"{'='*60}\n")
    
    # Initialize agents
    researcher_v2 = ResearchAgentV2(
        api_key=config.OPENROUTER_API_KEY,
        playwright_path=config.PLAYWRIGHT_BROWSERS_PATH
    )
    rag_manager = RAGManager(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    writer = WriterAgent(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    planner = PlannerAgent(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    scorer = BlogScorer(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    
    # Step 1: Enhanced Research with browser automation
    print(f"🔍 Step 1/7: Enhanced research with browser automation...")
    print(f"   Searching for: {topic}")
    
    try:
        articles = await researcher_v2.search_and_extract_articles(
            query=topic,
            max_articles=config.MAX_ARTICLES_TO_EXTRACT
        )
        
        if not articles:
            print("❌ No articles found. Falling back to original researcher.")
            return None
        
        print(f"✓ Found {len(articles)} articles with detailed content")
        
        # Convert articles to research data format for RAG
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
        
        print(f"✓ Converted to research data format")
        
    except Exception as e:
        print(f"❌ Error in enhanced research: {e}")
        return None
    
    # Step 2: Build RAG knowledge base
    print(f"\n📚 Step 2/7: Building knowledge base...")
    rag_manager.ingest_research(research_data)
    print("✓ Knowledge base ready")
    
    # Step 3: Create blog plan
    print(f"\n📋 Step 3/7: Planning blog structure...")
    
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
    
    # Step 4: Generate introduction
    print(f"\n✍️  Step 4/7: Generating introduction...")
    
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
    
    # Step 5: Generate sections
    print(f"\n✍️  Step 5/7: Generating sections...")
    
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
    
    # Step 6: Stitch content together
    print(f"\n🔗 Step 6/7: Stitching content together...")
    
    final_blog_parts = [intro_content] + section_contents
    final_blog = "\n\n".join(final_blog_parts)
    
    print(f"✓ Blog assembled")
    
    # Step 7: Save output
    print(f"\n💾 Step 7/7: Saving output...")
    
    # Create output directory if it doesn't exist
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate filename
    safe_topic = topic.replace(' ', '_').replace('/', '_')[:30]
    filename = f"{output_dir}/blog_v2_{safe_topic}.md"
    
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
        f.write(f"- **Research Method**: Enhanced Browser Automation (Researcher V2)\n")
        
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
    print(f"   - Research method: Enhanced Browser Automation")
    print(f"{'='*60}\n")
    
    return filename


if __name__ == "__main__":
    # Example usage
    asyncio.run(generate_blog_with_researcher_v2(
        topic="answer engine optimization",
        target_keywords=["AEO", "answer engine optimization", "AI"]
    ))

