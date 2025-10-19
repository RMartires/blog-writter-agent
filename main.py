from agents.researcher import ResearchAgent
from agents.rag_manager import RAGManager
from agents.writer import WriterAgent
from agents.scorer import BlogScorer
from agents.planner import PlannerAgent
import config
import os
import re
import uuid
from datetime import datetime
from typing import List
from langsmith import traceable


@traceable(name="BlogGeneration")
def generate_blog(topic: str, target_keywords: List[str] = None):
    """
    Generate a blog post using planner-based section-by-section generation
    
    Args:
        topic: The blog post topic
        target_keywords: Optional list of target keywords for SEO optimization
        
    Returns:
        Path to the generated blog post file
    """
    # Set default keywords if none provided
    if target_keywords is None:
        target_keywords = []
    
    # Validate API keys
    if not config.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables")
    if not config.TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not found in environment variables")
    
    # Generate session ID for LangSmith tracing
    session_id = str(uuid.uuid4())
    session_start = datetime.now()
    
    print(f"\n{'='*60}")
    print(f"AI Blog Writer Agent (Planner-Based)")
    print(f"Session ID: {session_id}")
    print(f"{'='*60}")
    print(f"Topic: {topic}")
    print(f"Model: {config.OPENROUTER_MODEL}")
    if target_keywords:
        keywords_str = ", ".join(target_keywords)
        print(f"Target Keywords: {keywords_str}")
    print(f"Section Score Threshold: 70/100")
    print(f"LangSmith Tracing: Enabled")
    print(f"{'='*60}\n")
    
    # Initialize agents with session ID for trace grouping
    researcher = ResearchAgent(config.TAVILY_API_KEY)
    rag_manager = RAGManager(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    writer = WriterAgent(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL, session_id=session_id)
    planner = PlannerAgent(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL, session_id=session_id)
    scorer = BlogScorer(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL, session_id=session_id)
    
    # Step 1: Research
    print(f"🔍 Step 1/7: Researching '{topic}'...")
    research_data = researcher.search(
        f"{topic}",
        max_results=5
    )
    
    if not research_data:
        print("❌ No research data found. Aborting.")
        return None
    
    print(f"✓ Found {len(research_data)} relevant sources")
    
    # Step 2: Build RAG knowledge base
    print(f"\n📚 Step 2/7: Building knowledge base...")
    rag_manager.ingest_research(research_data)
    print("✓ Knowledge base ready")
    
    # Step 3: Create blog plan
    print(f"\n📋 Step 3/7: Planning blog structure...")
    
    # Create research summary for planner
    research_summary = "\n".join([
        f"- {r['title']}: {r['content']}" 
        for r in research_data
    ])
    
    try:
        plan = planner.create_plan(
            topic=topic,
            target_keywords=target_keywords,
            research_summary=research_summary
        )
        
        print(f"✓ Plan created: '{plan.title}'")
        print(f"  Intro guidance: {plan.intro[:100] if plan.intro else 'None'}...")
        print(f"  Sections ({len(plan.sections)}):")
        for i, section in enumerate(plan.sections, 1):
            desc = f" - {section.description[:60]}..." if section.description else ""
            print(f"    {i}. {section.heading}{desc}")
    except Exception as e:
        print(f"❌ Error creating plan: {e}")
        return None
    
    # Step 4: Generate introduction
    print(f"\n✍️  Step 4/7: Generating introduction...")
    
    # Retrieve general context for intro
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
    
    # Step 5: Sequential section generation with scoring
    print(f"\n✍️  Step 5/7: Generating sections sequentially...")
    
    section_contents = []
    section_scores = []
    SECTION_THRESHOLD = 70  # Lower threshold for individual sections
    
    for i, section in enumerate(plan.sections, 1):
        print(f"\n  📝 Section {i}/{len(plan.sections)}: {section.heading}")
        if section.description:
            print(f"      Description: {section.description[:80]}...")
        
        # NEW: Section planning stage
        print(f"      🎯 Planning section structure...")
        section_query = f"{topic} {section.heading}"
        section_context = rag_manager.retrieve_context(section_query, k=3)
        
        # Format context for section planning
        research_context = "\n".join([
            f"- {doc.metadata.get('title', 'Source')}: {doc.page_content}" 
            for doc in section_context
        ])
        
        try:
            section_plan = planner.plan_section(
                section=section,
                topic=topic,
                research_context=research_context
            )
            
            if section_plan.subsections:
                print(f"      Subsections planned: {len(section_plan.subsections)}")
            else:
                print(f"      No subsections needed - single flow section")
        except Exception as e:
            print(f"      ❌ Error planning section: {e}")
            return None
        
        # Generate section using new method
        try:
            section_content = writer.generate_section_with_subsections(
                section_plan=section_plan,
                topic=topic,
                context_docs=section_context,
                previous_sections=section_contents,
                rag_manager=rag_manager
            )
            word_count = BlogScorer.count_words(section_content)
            
            # Validate that the section contains the expected heading
            expected_heading = f"## {section.heading}"
            if expected_heading not in section_content:
                print(f"     ⚠️  Warning: Generated section may not have correct heading")
                print(f"     Expected: {expected_heading}")
                # Try to extract what heading was actually generated
                actual_headings = re.findall(r'^##\s+(.+)$', section_content, re.MULTILINE)
                if actual_headings:
                    print(f"     Found: ## {actual_headings[0]}")
            
            print(f"     ✓ Generated ({word_count} words)")
        except Exception as e:
            print(f"     ❌ Error generating section: {e}")
            return None
        
        # Add to collection
        section_contents.append(section_content)
    
    # Step 6: Stitch content together
    print(f"\n🔗 Step 6/7: Stitching content together...")
    
    final_blog_parts = []
    
    # Add introduction
    final_blog_parts.append(intro_content)
    
    # Add all sections
    final_blog_parts.extend(section_contents)
    
    # Combine
    final_blog = "\n\n".join(final_blog_parts)
    
    # Calculate average section score
    avg_section_score = sum(section_scores) / len(section_scores) if section_scores else 0
    
    print(f"✓ Blog assembled")
    print(f"  Average section score: {avg_section_score:.1f}/100")
    
    # Step 7: Save output
    print(f"\n💾 Step 7/7: Saving output...")
    
    # Create output directory if it doesn't exist
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate filename
    safe_topic = topic.replace(' ', '_').replace('/', '_')[:30]
    filename = f"{output_dir}/blog_{safe_topic}.md"
    
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
        f.write(f"- **Average Section Score**: {avg_section_score:.1f}/100\n")
        f.write(f"- **Total Sections**: {len(section_contents)}\n")
        if target_keywords:
            keywords_str = ", ".join(target_keywords)
            f.write(f"- **Target Keywords**: {keywords_str}\n")
        f.write(f"- **Word Count**: {total_word_count}\n")
        f.write(f"- **Readability (Flesch)**: {flesch_score:.1f}\n")
        f.write(f"- **Keyword Density**: {keyword_density:.2f}%\n")
        
        # Add individual section scores
        f.write("\n### Section Scores\n\n")
        for i, (section, score) in enumerate(zip(plan.sections, section_scores), 1):
            f.write(f"{i}. **{section.heading}**: {score}/100\n")
        
        f.write("\n---\n\n## Sources\n\n")
        
        # Add source citations
        for r in research_data:
            title = r.get('title', 'Untitled')
            url = r.get('url', '#')
            f.write(f"- [{title}]({url})\n")
    
    print(f"✓ Saved to: {filename}")
    
    # Print statistics
    session_duration = (datetime.now() - session_start).total_seconds()
    print(f"\n{'='*60}")
    print(f"📊 Final Statistics:")
    print(f"   - Word count: {total_word_count}")
    print(f"   - Average section score: {avg_section_score:.1f}/100")
    print(f"   - Number of sections: {len(section_contents)}")
    print(f"   - Sources used: {len(research_data)}")
    print(f"   - Flesch reading ease: {flesch_score:.1f}")
    print(f"   - Keyword density: {keyword_density:.2f}%")
    print(f"   - Session duration: {session_duration:.1f} seconds")
    print(f"   - Session ID: {session_id}")
    print(f"{'='*60}")
    print(f"🔍 LangSmith Tracing:")
    print(f"   - All LLM interactions have been logged to LangSmith")
    print(f"   - View detailed traces at: https://smith.langchain.com")
    print(f"   - Session ID for filtering: {session_id}")
    print(f"{'='*60}\n")
    
    return filename


if __name__ == "__main__":
    # User will edit this line to test different topics and keywords
    generate_blog(
        topic="answer engine optimization",
        target_keywords=["AEO", "answer engine optimization", "AI"]
    )

