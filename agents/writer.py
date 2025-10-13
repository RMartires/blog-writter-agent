from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import Document
from typing import List


class WriterAgent:
    """Agent responsible for generating blog posts using OpenRouter LLMs"""
    
    def __init__(self, openrouter_api_key: str, model: str):
        """
        Initialize writer agent with OpenRouter credentials
        
        Args:
            openrouter_api_key: OpenRouter API key
            model: Model name to use for generation
        """
        if not openrouter_api_key:
            raise ValueError("OpenRouter API key is required")
        
        self.llm = ChatOpenAI(
            openai_api_key=openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            model_name=model,
            temperature=0.7
        )
    
    def generate_blog_post(
        self, 
        topic: str, 
        context_docs: List[Document],
        style: str = "professional"
    ) -> str:
        """
        Generate a blog post using RAG context
        
        Args:
            topic: Blog post topic
            context_docs: Retrieved context documents from RAG
            style: Writing style (professional, casual, technical, etc.)
            
        Returns:
            Generated blog post as markdown string
        """
        # Format context from retrieved documents
        context = self._format_context(context_docs)
        
        # Create prompt template
        prompt = PromptTemplate(
            input_variables=["topic", "context", "style"],
            template="""You are an expert blog writer. Write a comprehensive, engaging blog post on the following topic.

Topic: {topic}

Writing Style: {style}

Use the following research context to ensure accuracy and depth:

{context}

Requirements:
- Write 1000-1500 words
- Include a compelling introduction that hooks the reader
- Organize content with clear sections using markdown headings (##, ###)
- Use bullet points or numbered lists where appropriate
- Include relevant examples and explanations
- Write in an engaging, informative tone
- Create a strong conclusion with key takeaways
- Use proper markdown formatting throughout
- Ensure the content is SEO-friendly with natural keyword usage

Blog Post:
"""
        )
        
        # Create and run the chain
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt)
            result = chain.run(topic=topic, context=context, style=style)
            return result
        except Exception as e:
            print(f"Error generating blog post: {e}")
            raise
    
    def _format_context(self, context_docs: List[Document]) -> str:
        """
        Format context documents into a readable string
        
        Args:
            context_docs: List of Document objects
            
        Returns:
            Formatted context string
        """
        if not context_docs:
            return "No additional context available."
        
        formatted_parts = []
        for i, doc in enumerate(context_docs, 1):
            title = doc.metadata.get('title', 'Source')
            content = doc.page_content
            formatted_parts.append(f"[Source {i}: {title}]\n{content}\n")
        
        return "\n".join(formatted_parts)

