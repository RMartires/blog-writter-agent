# AI Blog Writer Agent

An AI-powered blog writing system that uses web research (Tavily API), RAG (Retrieval-Augmented Generation) with LangChain, and OpenRouter for flexible LLM access to generate high-quality blog posts.

## Features

- 🔍 **Web Research**: Automatically researches topics using Tavily API
- 📚 **RAG System**: Uses LangChain and FAISS for context-aware generation
- 🤖 **Flexible AI Models**: Access multiple LLMs via OpenRouter (including free models)
- 📝 **Quality Content**: Generates 1000-1500 word blog posts with proper structure
- 📖 **Source Citations**: Automatically includes source references
- 🔍 **Observability**: Built-in LangSmith integration for tracing and debugging

## Prerequisites

- Python 3.10 or higher
- OpenRouter API key (get it at https://openrouter.ai/)
- Tavily API key (get it at https://tavily.com/)

## Installation

1. **Navigate to the project directory**:
   ```bash
   cd "/media/mats/3c24094c-800b-4576-a390-d23a6d7a02291/workspace/test_ai_gen/blog writter"
   ```

2. **Activate the virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Create a `.env` file** in the project root:
   ```bash
   nano .env
   ```

4. **Add your API keys** to the `.env` file:
   ```
   OPENROUTER_API_KEY=your_openrouter_key_here
   TAVILY_API_KEY=your_tavily_key_here
   
   # Optional: LangSmith for observability and debugging
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_api_key_here
   LANGCHAIN_PROJECT=blog-writer-agent
   ```

## Usage

### Basic Usage

1. **Activate the virtual environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Edit the topic in `main.py`**:
   ```python
   if __name__ == "__main__":
       generate_blog("Your Topic Here")
   ```

3. **Run the script**:
   ```bash
   python main.py
   ```

4. **Find your blog post** in the `output/` directory

### Changing the AI Model

Edit `config.py` to change the OpenRouter model:

```python
# Free models (recommended for testing)
OPENROUTER_MODEL = "meta-llama/llama-3-70b-instruct"
# OPENROUTER_MODEL = "google/gemma-7b-it:free"
# OPENROUTER_MODEL = "mistralai/mistral-7b-instruct:free"

# Paid models (better quality)
# OPENROUTER_MODEL = "anthropic/claude-3.5-sonnet"
# OPENROUTER_MODEL = "openai/gpt-4-turbo"
```

## Project Structure

```
blog-writer-agent/
├── venv/                    # Virtual environment
├── .env                     # API keys (create this)
├── .gitignore              
├── requirements.txt         # Dependencies
├── config.py               # Configuration
├── main.py                 # Main script
├── agents/
│   ├── __init__.py
│   ├── researcher.py       # Tavily web search agent
│   ├── rag_manager.py      # RAG system with FAISS
│   └── writer.py           # Blog post generation agent
└── output/                 # Generated blog posts
```

## How It Works

1. **Research Phase**: The Researcher Agent searches the web using Tavily API to gather relevant, up-to-date information about your topic.

2. **RAG Building**: The RAG Manager processes the research data, splits it into chunks, and stores it in an in-memory FAISS vector store with embeddings.

3. **Context Retrieval**: When generating content, the system retrieves the most relevant chunks from the vector store.

4. **Content Generation**: The Writer Agent uses an OpenRouter LLM with the retrieved context to generate a comprehensive, well-structured blog post.

5. **Output**: The final blog post is saved as a markdown file with source citations.

## Example Output

```
output/blog_The_Future_of_AI_in_Healthcare.md
```

The output includes:
- Properly formatted markdown
- Clear section headings
- 1000-1500 words of content
- Source citations at the end

## Customization

### Adjust Research Depth

Edit `main.py` to change the number of sources:
```python
research_data = researcher.search(
    f"Latest information about {topic}",
    max_results=10  # Increase for more sources
)
```

### Change Writing Style

Modify the style parameter in `main.py`:
```python
blog_post = writer.generate_blog_post(
    topic=topic,
    context_docs=context_docs,
    style="technical"  # Options: professional, casual, technical, etc.
)
```

### Adjust RAG Parameters

Edit `agents/rag_manager.py`:
```python
chunk_size=1000,      # Increase for larger chunks
chunk_overlap=200,    # Adjust overlap
```

## Troubleshooting

### "API key not found" error
Make sure you've created a `.env` file with both API keys.

### Import errors
Ensure you've activated the virtual environment:
```bash
source venv/bin/activate
```

### "No research data found"
Check your Tavily API key and internet connection.

### Model not available
Some OpenRouter models require credits. Check available free models at https://openrouter.ai/models

## LangSmith Observability

The system includes built-in LangSmith integration for comprehensive observability:

### What You Get
- **Complete LLM Interaction Logs**: Every prompt and response is automatically logged
- **Agent Identification**: See which agent (Writer, Planner, Scorer) made each call
- **Session Tracking**: Group related interactions by session ID
- **Performance Metrics**: Response times, token usage, and costs
- **Error Tracking**: Automatic error logging and debugging information
- **Visual Interface**: Web dashboard at https://smith.langchain.com

### Setup (Optional)
1. **Sign up for LangSmith** (free tier available): https://smith.langchain.com
2. **Get your API key** from the LangSmith dashboard
3. **Add to your `.env` file**:
   ```
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_api_key_here
   LANGCHAIN_PROJECT=blog-writer-agent
   ```

### Viewing Traces
- After running the blog generator, check the console output for session information
- Visit https://smith.langchain.com to view detailed traces
- Filter by session ID to see all interactions for a specific run
- Analyze performance, debug issues, and optimize prompts

## Cost Estimates

- **Tavily API**: Free tier includes 1,000 searches/month
- **OpenRouter**: 
  - Free models: $0
  - Paid models: ~$0.01-0.10 per blog post (depending on model)
- **LangSmith**: Free tier includes 1,000 traces/month

## License

MIT License - Feel free to modify and use as needed.

## Enter to venv
source venv/bin/activate