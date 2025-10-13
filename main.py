from agents.researcher import ResearchAgent
from agents.rag_manager import RAGManager
from agents.writer import WriterAgent
import config
import os


def generate_blog(topic: str):
    """
    Generate a blog post on the given topic using AI agents
    
    Args:
        topic: The blog post topic
        
    Returns:
        Path to the generated blog post file
    """
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
    print(f"\n🎯 Step 3/5: Retrieving relevant context...")
    context_docs = rag_manager.retrieve_context(topic, k=4)
    print(f"✓ Retrieved {len(context_docs)} context chunks")
    
    # Step 4: Generate blog post
    print(f"\n✍️  Step 4/5: Generating blog post...")
    try:
        blog_post = writer.generate_blog_post(
            topic=topic,
            context_docs=context_docs,
            style="professional"
        )
        print("✓ Blog post generated successfully")
    except Exception as e:
        print(f"❌ Error generating blog post: {e}")
        return None
    
    # Step 5: Save output
    print(f"\n💾 Step 5/5: Saving output...")
    
    # Create output directory if it doesn't exist
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate filename
    safe_topic = topic.replace(' ', '_').replace('/', '_')[:30]
    filename = f"{output_dir}/blog_{safe_topic}.md"
    
    # Write blog post with sources
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# {topic}\n\n")
        f.write(blog_post)
        f.write("\n\n---\n\n## Sources\n\n")
        
        # Add source citations
        for doc in context_docs:
            title = doc.metadata.get('title', 'Untitled')
            url = doc.metadata.get('source', '#')
            f.write(f"- [{title}]({url})\n")
    
    print(f"✓ Saved to: {filename}")
    
    # Print statistics
    word_count = len(blog_post.split())
    print(f"\n{'='*60}")
    print(f"📊 Statistics:")
    print(f"   - Word count: {word_count}")
    print(f"   - Sources used: {len(research_data)}")
    print(f"   - Context chunks: {len(context_docs)}")
    print(f"{'='*60}\n")
    
    return filename


if __name__ == "__main__":
    # User will edit this line to test different topics
    generate_blog("The Future of AI in Healthcare")

