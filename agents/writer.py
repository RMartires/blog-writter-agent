from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from typing import List
from agents.lib.openrouter_wrapper import OpenRouterLLM
import config


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
        
        # Use wrapper with rate limiting and retry logic
        self.llm = OpenRouterLLM(
            api_key=openrouter_api_key,
            model=model,
            temperature=0.7,
            min_request_interval=config.API_MIN_REQUEST_INTERVAL,
            max_retries=config.API_MAX_RETRIES,
            retry_delay=config.API_RETRY_DELAY
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
            template="""
<systemMessage>            
You are an expert blog writer. Write a comprehensive, engaging blog post on the following topic.

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

</systemMessage>
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
    
    def rewrite_blog_post(
        self,
        original_blog: str,
        topic: str,
        score_feedback: dict,
        context_docs: List[Document],
        target_keywords: List[str],
        iteration: int
    ) -> str:
        """
        Rewrite a blog post based on scoring feedback
        
        Args:
            original_blog: The original blog content to improve
            topic: Blog post topic
            score_feedback: Scoring feedback dictionary from BlogScorer
            context_docs: Retrieved context documents from RAG
            target_keywords: Target keywords for SEO
            iteration: Current iteration number
            
        Returns:
            Rewritten blog post as markdown string
        """
        # Format context from retrieved documents
        context = self._format_context(context_docs)
        
        # Format feedback
        feedback_str = self._format_feedback(score_feedback)
        
        # Format keywords
        keywords_str = ", ".join(target_keywords) if target_keywords else "None"
        
        # Create rewrite prompt
        prompt = PromptTemplate(
            input_variables=["topic", "original_blog", "feedback", "context", "keywords", "iteration"],
            template="""

<systemMessage>            
You are an expert blog writer tasked with improving a blog post based on detailed feedback.

TOPIC: {topic}
TARGET KEYWORDS: {keywords}
ITERATION: {iteration}

ORIGINAL BLOG POST:
{original_blog}

---

SCORING FEEDBACK AND AREAS FOR IMPROVEMENT:
{feedback}

---

RESEARCH CONTEXT (for accuracy):
{context}

---

YOUR TASK:
Rewrite the blog post to address ALL the feedback points and improvement suggestions above. 

REQUIREMENTS:
1. MAINTAIN all strengths mentioned in the feedback
2. FIX all weaknesses identified in each category
3. IMPLEMENT all improvement suggestions provided
4. For SEO: Naturally integrate target keywords into title, headings (H2, H3), and content
5. For Readability: Use varied sentence structures, clear transitions, active voice
6. For Content Quality: Add more examples, data, or depth where suggested
7. For Engagement: Strengthen the hook, add storytelling elements, include clear CTAs
8. For Structure: Ensure proper markdown formatting, heading hierarchy, optimal length (1000-1500 words)

IMPORTANT:
- Keep the same general structure and main points unless feedback suggests otherwise
- Maintain factual accuracy using the research context provided
- Make the improvements feel natural, not forced
- Write in a professional, engaging tone
- Use proper markdown formatting throughout

</systemMessage>
"""
        )
        
        # Create and run the chain
        try:
            from langchain.chains import LLMChain
            chain = LLMChain(llm=self.llm, prompt=prompt)
            result = chain.run(
                topic=topic,
                original_blog=original_blog,
                feedback=feedback_str,
                context=context,
                keywords=keywords_str,
                iteration=iteration
            )
            return result
        except Exception as e:
            print(f"Error rewriting blog post: {e}")
            raise
    
    def _format_feedback(self, score_feedback: dict) -> str:
        """Format scoring feedback into a readable string for the LLM"""
        total_score = score_feedback.get('total_score', 0)
        category_scores = score_feedback.get('category_scores', {})
        feedback = score_feedback.get('feedback', {})
        suggestions = score_feedback.get('improvement_suggestions', [])
        
        feedback_parts = [
            f"OVERALL SCORE: {total_score}/100\n",
            "CATEGORY BREAKDOWN:"
        ]
        
        # Add each category's score and feedback
        for category, score_data in category_scores.items():
            score = score_data.get('score', 0)
            max_score = score_data.get('max', 0)
            percentage = (score / max_score * 100) if max_score > 0 else 0
            category_feedback = feedback.get(category, "No feedback")
            
            category_name = category.replace('_', ' ').title()
            feedback_parts.append(f"\n{category_name}: {score}/{max_score} ({percentage:.0f}%)")
            feedback_parts.append(f"Feedback: {category_feedback}")
        
        # Add improvement suggestions
        if suggestions:
            feedback_parts.append("\nIMPROVEMENT SUGGESTIONS:")
            for i, suggestion in enumerate(suggestions, 1):
                feedback_parts.append(f"{i}. {suggestion}")
        
        return "\n".join(feedback_parts)
    
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

