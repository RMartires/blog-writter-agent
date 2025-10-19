from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from typing import List, Optional
from agents.lib.openrouter_wrapper import OpenRouterLLM
from agents.models import BlogPlan, BlogSection, SubSection
import config


class WriterAgent:
    """Agent responsible for generating blog posts using OpenRouter LLMs"""
    
    def __init__(self, openrouter_api_key: str, model: str, session_id: str = None):
        """
        Initialize writer agent with OpenRouter credentials
        
        Args:
            openrouter_api_key: OpenRouter API key
            model: Model name to use for generation
            session_id: Optional session ID for trace grouping
        """
        if not openrouter_api_key:
            raise ValueError("OpenRouter API key is required")
        
        # Use wrapper with rate limiting and retry logic
        self.llm = OpenRouterLLM(
            api_key=openrouter_api_key,
            model=model,
            temperature=0.7,
            agent_name="WriterAgent",
            session_id=session_id,
            min_request_interval=config.API_MIN_REQUEST_INTERVAL,
            max_retries=config.API_MAX_RETRIES,
            retry_delay=config.API_RETRY_DELAY
        )
    
        
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
    
    def generate_intro(
        self,
        topic: str,
        plan: BlogPlan,
        context_docs: List[Document],
        length_guidance: str = "moderate"
    ) -> str:
        """
        Generate introduction section based on blog plan
        
        Args:
            topic: Blog post topic
            plan: The complete blog plan with structure
            context_docs: Retrieved context documents from RAG
            length_guidance: Length guidance - 'brief', 'moderate', or 'comprehensive'
            
        Returns:
            Generated introduction as markdown string
        """
        # Format context from retrieved documents
        context = self._format_context(context_docs)
        
        # Format the plan structure for context
        sections_preview = "\n".join([f"- {section.heading}" for section in plan.sections])
        intro_guidance = plan.intro if plan.intro else "Hook the reader and introduce the topic"
        
        # Determine word count target based on length guidance
        if length_guidance == "brief":
            word_target = "100-150 words"
            paragraph_guidance = "1-2 paragraphs"
        elif length_guidance == "comprehensive":
            word_target = "250-400 words"
            paragraph_guidance = "3-4 paragraphs"
        else:  # moderate
            word_target = "150-250 words"
            paragraph_guidance = "2-3 paragraphs"
        
        # Create prompt template
        prompt = PromptTemplate(
            input_variables=["topic", "title", "intro_guidance", "sections_preview", "context", "word_target", "paragraph_guidance"],
            template="""
<systemMessage>
You are an expert blog writer creating an engaging introduction.

TOPIC: {topic}
BLOG TITLE: {title}

INTRODUCTION GUIDANCE: {intro_guidance}

UPCOMING SECTIONS:
{sections_preview}

RESEARCH CONTEXT:
{context}

YOUR TASK:
Write a compelling introduction ({paragraph_guidance}, {word_target}) that:
1. Opens with a strong hook to grab attention
2. Introduces the topic and its importance
3. Previews what the reader will learn (reference the sections)
4. Sets an engaging, professional tone
5. Uses natural keyword integration

Requirements:
- Use markdown formatting
- Write in second person ("you") where appropriate
- Be conversational yet professional
- Create curiosity about the content ahead
- Target approximately {word_target}

Write ONLY the introduction content, no headings.
</systemMessage>
"""
        )
        
        # Create and run the chain
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt)
            result = chain.run(
                topic=topic,
                title=plan.title,
                intro_guidance=intro_guidance,
                sections_preview=sections_preview,
                context=context,
                word_target=word_target,
                paragraph_guidance=paragraph_guidance
            )
            return result.strip()
        except Exception as e:
            print(f"Error generating introduction: {e}")
            raise
    
    def generate_section(
        self,
        section: BlogSection,
        topic: str,
        context_docs: List[Document],
        previous_sections: List[str] = None
    ) -> str:
        """
        Generate content for a single blog section
        
        Args:
            section: BlogSection object with heading and description
            topic: Overall blog topic
            context_docs: Retrieved context documents relevant to this section
            previous_sections: List of previously generated section contents for context
            
        Returns:
            Generated section content as markdown string
        """
        # Format context from retrieved documents
        context = self._format_context(context_docs)
        
        # Format previous sections for context awareness
        previous_context = ""
        if previous_sections:
            previous_context = "\n\nPREVIOUSLY COVERED:\n" + "\n---\n".join(previous_sections[-2:])  # Last 2 sections
        
        section_guidance = section.description if section.description else "Provide comprehensive coverage of this topic"
        
        # Create prompt template
        prompt = PromptTemplate(
            input_variables=["topic", "heading", "section_guidance", "context", "previous_context"],
            template="""
<systemMessage>
You are an expert blog writer creating a specific section of a blog post.

OVERALL TOPIC: {topic}

CRITICAL: You MUST use this EXACT heading as your H2 title:
## {heading}

SECTION GUIDANCE: {section_guidance}

RESEARCH CONTEXT FOR THIS SECTION:
{context}
{previous_context}

YOUR TASK:
Write this section (250-350 words) with:
1. Start with the EXACT section heading as H2: ## {heading}
2. Provide comprehensive, valuable information specific to "{heading}"
3. Use specific examples, data, or actionable tips
4. Include subheadings (###) if needed for clarity
5. Use bullet points or numbered lists where appropriate
6. Maintain logical flow and connection with previous content
7. Write in an engaging, professional tone
8. Natural keyword integration

CRITICAL REQUIREMENTS:
- You MUST use the exact heading "## {heading}" - do NOT change it or create a different heading
- Focus ONLY on the topic indicated by this heading
- Use proper markdown formatting
- Be informative and practical
- Keep paragraphs concise (3-4 sentences)
- Ensure content flows naturally from what was previously discussed
- Do NOT repeat information from previous sections
- Do NOT write about topics from previous sections

Write the complete section starting with: ## {heading}
</systemMessage>
"""
        )
        
        # Create and run the chain
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt)
            result = chain.run(
                topic=topic,
                heading=section.heading,
                section_guidance=section_guidance,
                context=context,
                previous_context=previous_context
            )
            return result.strip()
        except Exception as e:
            print(f"Error generating section '{section.heading}': {e}")
            raise
    
    def improve_section(
        self,
        section_content: str,
        section_heading: str,
        score_feedback: dict,
        context_docs: List[Document]
    ) -> str:
        """
        Improve a section based on scoring feedback (one pass only)
        
        Args:
            section_content: The original section content to improve
            section_heading: The heading of this section
            score_feedback: Scoring feedback dictionary from BlogScorer
            context_docs: Retrieved context documents for accuracy
            
        Returns:
            Improved section content as markdown string
        """
        # Format context from retrieved documents
        context = self._format_context(context_docs)
        
        # Format feedback
        feedback_str = self._format_feedback(score_feedback)
        
        # Create improvement prompt
        prompt = PromptTemplate(
            input_variables=["section_heading", "section_content", "feedback", "context"],
            template="""
<systemMessage>
You are an expert blog writer improving a section based on feedback.

CRITICAL: You MUST keep this EXACT heading:
## {section_heading}

ORIGINAL SECTION CONTENT:
{section_content}

---

SCORING FEEDBACK:
{feedback}

---

RESEARCH CONTEXT (for accuracy):
{context}

---

YOUR TASK:
Rewrite this section to address ALL the feedback points above.

CRITICAL REQUIREMENTS:
1. You MUST use the EXACT heading: ## {section_heading} - do NOT change it
2. Keep the same general topic focused on "{section_heading}"
3. Fix all weaknesses identified in each category
4. Implement improvement suggestions
5. Enhance readability, SEO, and engagement
6. Keep the section length appropriate (250-350 words)
7. Ensure natural, professional tone
8. Use proper markdown formatting

Write the improved section starting with: ## {section_heading}
</systemMessage>
"""
        )
        
        # Create and run the chain
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt)
            result = chain.run(
                section_heading=section_heading,
                section_content=section_content,
                feedback=feedback_str,
                context=context
            )
            return result.strip()
        except Exception as e:
            print(f"Error improving section '{section_heading}': {e}")
            raise
    
    def generate_subsection(
        self,
        subsection: SubSection,
        section_heading: str,
        topic: str,
        context_docs: List[Document],
        previous_content: str = ""
    ) -> str:
        """
        Generate content for a single subsection (H3)
        
        Args:
            subsection: SubSection object with H3 heading and description
            section_heading: Parent section H2 heading for context
            topic: Overall blog topic
            context_docs: Retrieved context documents
            previous_content: Previously generated subsection content in this section
            
        Returns:
            Generated subsection content as markdown string
        """
        # Format context from retrieved documents
        context = self._format_context(context_docs)
        
        # Format previous content for context awareness
        previous_context = ""
        if previous_content:
            previous_context = f"\n\nPREVIOUS SUBSECTIONS IN THIS SECTION:\n{previous_content}\n"
        
        subsection_guidance = subsection.description if subsection.description else "Provide comprehensive coverage of this subsection topic"
        
        # Create prompt template
        prompt = PromptTemplate(
            input_variables=["topic", "section_heading", "subsection_heading", "subsection_guidance", "context", "previous_context"],
            template="""
<systemMessage>
You are an expert blog writer creating a specific subsection of a blog post.

OVERALL TOPIC: {topic}
PARENT SECTION: {section_heading}

CRITICAL: You MUST use this EXACT heading as your H3 title:
### {subsection_heading}

SUBSECTION GUIDANCE: {subsection_guidance}

RESEARCH CONTEXT FOR THIS SUBSECTION:
{context}
{previous_context}

YOUR TASK:
Write this subsection (150-250 words) with:
1. Start with the EXACT subsection heading as H3: ### {subsection_heading}
2. Provide comprehensive, valuable information specific to "{subsection_heading}"
3. Use specific examples, data, or actionable tips where relevant
4. Use bullet points or numbered lists where appropriate
5. Maintain logical flow and connection with the parent section
6. Write in an engaging, professional tone
7. Natural keyword integration

CRITICAL REQUIREMENTS:
- You MUST use the exact heading "### {subsection_heading}" - do NOT change it
- Focus ONLY on the topic indicated by this subsection heading
- Use proper markdown formatting
- Be informative and practical
- Keep paragraphs concise (2-3 sentences)
- Ensure content flows naturally within the parent section
- Do NOT repeat information from previous subsections
- Do NOT write about topics from other subsections

Write the complete subsection starting with: ### {subsection_heading}
</systemMessage>
"""
        )
        
        # Create and run the chain
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt)
            result = chain.run(
                topic=topic,
                section_heading=section_heading,
                subsection_heading=subsection.heading,
                subsection_guidance=subsection_guidance,
                context=context,
                previous_context=previous_context
            )
            return result.strip()
        except Exception as e:
            print(f"Error generating subsection '{subsection.heading}': {e}")
            raise
    
    def generate_section_with_subsections(
        self,
        section: BlogSection,
        topic: str,
        context_docs: List[Document],
        previous_sections: List[str] = None,
        rag_manager=None
    ) -> str:
        """
        Generate a section with optional subsections based on section plan
        
        If subsections exist, generates each subsection individually and combines them.
        If no subsections, falls back to generate_section behavior.
        
        Args:
            section: BlogSection object with heading, description, and optional subsections
            topic: Overall blog topic
            context_docs: Retrieved context documents relevant to this section
            previous_sections: List of previously generated section contents for context
            rag_manager: RAGManager instance for retrieving subsection-specific context
            
        Returns:
            Generated section content as markdown string
        """
        # If no subsections, use existing generate_section logic
        if not section.subsections:
            return self.generate_section(
                section=section,
                topic=topic,
                context_docs=context_docs,
                previous_sections=previous_sections
            )
        
        # Generate subsections individually
        print(f"      📝 Generating {len(section.subsections)} subsections...")
        
        # Start with the main section heading
        section_content = f"## {section.heading}\n\n"
        
        # Add section description if available
        if section.description:
            section_content += f"{section.description}\n\n"
        
        # Generate each subsection
        subsection_contents = []
        for i, subsection in enumerate(section.subsections, 1):
            print(f"        📝 Subsection {i}/{len(section.subsections)}: {subsection.heading}")
            
            # Retrieve subsection-specific context from RAG
            subsection_context = context_docs  # Default to section context
            if rag_manager:
                subsection_query = f"{topic} {section.heading} {subsection.heading}"
                subsection_context = rag_manager.retrieve_context(subsection_query, k=3)
                print(f"        🔍 Retrieved {len(subsection_context)} context docs for subsection")
            
            # Build previous content context for this subsection
            previous_content = "\n\n".join(subsection_contents)
            
            try:
                subsection_content = self.generate_subsection(
                    subsection=subsection,
                    section_heading=section.heading,
                    topic=topic,
                    context_docs=subsection_context,
                    previous_content=previous_content
                )
                subsection_contents.append(subsection_content)
                print(f"        ✓ Generated subsection ({len(subsection_content.split())} words)")
            except Exception as e:
                print(f"        ❌ Error generating subsection '{subsection.heading}': {e}")
                # Add a placeholder for failed subsection
                subsection_contents.append(f"### {subsection.heading}\n\n*Content generation failed for this subsection.*")
        
        # Combine all subsection content
        section_content += "\n\n".join(subsection_contents)
        
        return section_content

