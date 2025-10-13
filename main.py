from agents.researcher import ResearchAgent
from agents.rag_manager import RAGManager
from agents.writer import WriterAgent
from agents.scorer import BlogScorer
from agents.iteration_manager import IterationManager
import config
import os
from typing import List


def generate_blog(topic: str, target_keywords: List[str] = None):
    """
    Generate a blog post on the given topic using AI agents with iterative scoring
    
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
    
    print(f"\n{'='*60}")
    print(f"AI Blog Writer Agent")
    print(f"{'='*60}")
    print(f"Topic: {topic}")
    print(f"Model: {config.OPENROUTER_MODEL}")
    if target_keywords:
        keywords_str = ", ".join(target_keywords)
        print(f"Target Keywords: {keywords_str}")
    print(f"Max Iterations: {config.MAX_ITERATIONS}")
    print(f"Score Threshold: {config.MIN_SCORE_THRESHOLD}")
    print(f"{'='*60}\n")
    
    # Initialize agents
    researcher = ResearchAgent(config.TAVILY_API_KEY)
    rag_manager = RAGManager(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    writer = WriterAgent(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    
    # Step 1: Research
    print(f"🔍 Step 1/5: Researching '{topic}'...")
    research_data = researcher.search(
        f"{topic}",
        max_results=5
    )
    
    if not research_data:
        print("❌ No research data found. Aborting.")
        return None
    
    print(f"✓ Found {len(research_data)} relevant sources")
    
    # Step 2: Build RAG knowledge base
    print(f"\n📚 Step 2/5: Building knowledge base...")
    rag_manager.ingest_research(research_data)
    print("✓ Knowledge base ready")
    
    # Step 3: Retrieve context
    print(f"\n🎯 Step 3/7: Retrieving relevant context...")
    context_docs = rag_manager.retrieve_context(topic, k=4)
    print(f"✓ Retrieved {len(context_docs)} context chunks")
    
    # Step 4-6: Iterative writing and scoring
    print(f"\n✍️  Step 4/7: Iterative writing and scoring...")
    
    # Initialize scorer and iteration manager
    scorer = BlogScorer(config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    iteration_manager = IterationManager(config)
    
    # Run iterations
    try:
        result = iteration_manager.run_iterations(
            topic=topic,
            target_keywords=target_keywords,
            context_docs=context_docs,
            writer=writer,
            scorer=scorer
        )
        
        final_blog = result['best_blog']
        final_score = result['best_score']
        iteration_count = result['iteration_count']
        best_iteration = result['best_iteration']
        score_details = result['final_score_details']
        
        print(f"\n🎉 Completed {iteration_count} iteration(s)")
        print(f"📊 Best Score: {final_score}/100 (from iteration {best_iteration})")
        
    except Exception as e:
        print(f"❌ Error during iterative writing: {e}")
        return None
    
    # Step 7: Save output
    print(f"\n💾 Step 7/7: Saving output...")
    
    # Create output directory if it doesn't exist
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate filename
    safe_topic = topic.replace(' ', '_').replace('/', '_')[:30]
    filename = f"{output_dir}/blog_{safe_topic}.md"
    
    # Write blog post with sources and metadata
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# {topic}\n\n")
        f.write(final_blog)
        f.write("\n\n---\n\n")
        
        # Add metadata section
        f.write("## Metadata\n\n")
        f.write(f"- **Final Score**: {final_score}/100\n")
        f.write(f"- **Iterations**: {iteration_count}\n")
        f.write(f"- **Best Iteration**: {best_iteration}\n")
        if target_keywords:
            keywords_str = ", ".join(target_keywords)
            f.write(f"- **Target Keywords**: {keywords_str}\n")
        f.write(f"- **Word Count**: {score_details['metrics']['word_count']}\n")
        f.write(f"- **Readability (Flesch)**: {score_details['metrics']['flesch_score']:.1f}\n")
        f.write(f"- **Keyword Density**: {score_details['metrics']['keyword_density']:.2f}%\n")
        
        # Add category scores
        f.write("\n### Category Scores\n\n")
        for category, score_data in score_details['category_scores'].items():
            score = score_data['score']
            max_score = score_data['max']
            percentage = (score / max_score * 100) if max_score > 0 else 0
            category_name = category.replace('_', ' ').title()
            f.write(f"- **{category_name}**: {score}/{max_score} ({percentage:.0f}%)\n")
        
        f.write("\n---\n\n## Sources\n\n")
        
        # Add source citations
        for doc in context_docs:
            title = doc.metadata.get('title', 'Untitled')
            url = doc.metadata.get('source', '#')
            f.write(f"- [{title}]({url})\n")
    
    print(f"✓ Saved to: {filename}")
    
    # Print statistics
    word_count = score_details['metrics']['word_count']
    print(f"\n{'='*60}")
    print(f"📊 Final Statistics:")
    print(f"   - Word count: {word_count}")
    print(f"   - Final score: {final_score}/100")
    print(f"   - Iterations completed: {iteration_count}")
    print(f"   - Sources used: {len(research_data)}")
    print(f"   - Context chunks: {len(context_docs)}")
    print(f"   - Flesch reading ease: {score_details['metrics']['flesch_score']:.1f}")
    print(f"{'='*60}\n")
    
    return filename


if __name__ == "__main__":
    # User will edit this line to test different topics and keywords
    generate_blog(
        topic="The Future of AI in Healthcare",
        target_keywords=["AI healthcare", "artificial intelligence", "medical AI", "healthcare technology"]
    )

