from typing import List
import json
import re
from agents.lib.openrouter_wrapper import OpenRouterLLM
from agents.models import BlogPlan, BlogSection
import config


class PlannerAgent:
    """Agent responsible for planning blog structure before writing"""
    
    def __init__(self, openrouter_api_key: str, model: str, session_id: str = None):
        """
        Initialize planner agent with OpenRouter credentials
        
        Args:
            openrouter_api_key: OpenRouter API key
            model: Model name to use for planning
            session_id: Optional session ID for trace grouping
        """
        if not openrouter_api_key:
            raise ValueError("OpenRouter API key is required")
        
        # Use wrapper with rate limiting and retry logic
        self.llm = OpenRouterLLM(
            api_key=openrouter_api_key,
            model=model,
            temperature=0.5,  # Medium temperature for creative but structured planning
            agent_name="PlannerAgent",
            session_id=session_id,
            min_request_interval=config.API_MIN_REQUEST_INTERVAL,
            max_retries=config.API_MAX_RETRIES,
            retry_delay=config.API_RETRY_DELAY
        )
    
    def create_plan(
        self, 
        topic: str, 
        target_keywords: List[str],
        research_summary: str = ""
    ) -> BlogPlan:
        """
        Create a structured blog plan for the given topic
        
        Args:
            topic: Blog post topic
            target_keywords: List of target keywords for SEO
            research_summary: Optional summary of research findings
            
        Returns:
            Validated BlogPlan object
            
        Raises:
            Exception: If unable to generate valid plan after all retry attempts
        """
        # Create planning prompt
        prompt = self._create_planning_prompt(topic, target_keywords, research_summary)
        
        # Try multiple times to get valid structured output
        max_attempts = 5
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                print(f"🎯 Planning attempt {attempt + 1}/{max_attempts}...")
                response = self.llm.invoke(prompt)
                
                # Extract content from response
                response_content = response.content if hasattr(response, 'content') else str(response)
                
                # Debug: show first part of response
                response_preview = response_content[:150].replace('\n', ' ')
                print(f"   Response preview: {response_preview}...")
                
                # Parse and validate
                plan = self._parse_plan_response(response_content)
                print(f"✅ Successfully created plan with {plan.get_section_count()} sections")
                return plan
                    
            except Exception as e:
                last_error = e
                error_msg = str(e)[:200]
                print(f"❌ Attempt {attempt + 1}/{max_attempts} failed: {error_msg}")
                
                if attempt < max_attempts - 1:
                    if attempt >= 2:
                        # After 2 failures, try simplified prompt
                        print("🔄 Retrying with simplified prompt...")
                        prompt = self._create_simplified_prompt(topic, target_keywords)
        
        # If we get here, all attempts failed
        raise Exception(
            f"Failed to generate valid blog plan after {max_attempts} attempts. "
            f"Last error: {last_error}"
        )
    
    def _create_planning_prompt(
        self, 
        topic: str, 
        target_keywords: List[str],
        research_summary: str
    ) -> str:
        """Create the planning prompt for the LLM"""
        keywords_str = ", ".join([f"'{kw}'" for kw in target_keywords]) if target_keywords else "None provided"
        
        research_context = ""
        if research_summary:
            research_context = f"\nRESEARCH CONTEXT:\n{research_summary}\n"
        
        prompt = f"""You are an expert blog content planner. You must respond ONLY with valid JSON, no other text.

BLOG TOPIC: {topic}
TARGET KEYWORDS: {keywords_str}
{research_context}
YOUR TASK:
Create a comprehensive blog post structure with a clear outline of sections.

REQUIREMENTS:
1. Create a compelling title that includes the main keyword
2. Plan how many sections are required for this blog, looking at the context
3. Plan these sections that thoroughly cover the topic
4. Each section should have a clear, descriptive heading
5. Optionally provide a brief description of what each section should cover
6. Ensure logical flow from introduction to conclusion
7. Consider SEO - headings should be keyword-rich but natural
8. Think about reader engagement - sections should build upon each other

RESPONSE FORMAT (JSON):
{{
    "title": "Blog Post Title Here",
    "intro": "Brief description of what the introduction should cover (optional)",
    "sections": [
        {{
            "heading": "Section 1 Heading",
            "description": "What this section should cover (optional)"
        }},
        {{
            "heading": "Section 2 Heading",
            "description": "What this section should cover (optional)"
        }},
        ...
    ]
}}

CRITICAL: Your response must be ONLY valid JSON. Do not include any explanatory text, markdown formatting, or code blocks. Start your response with {{ and end with }}."""

        return prompt
    
    def _create_simplified_prompt(self, topic: str, target_keywords: List[str]) -> str:
        """Create a simplified prompt for fallback"""
        keywords_str = ", ".join(target_keywords) if target_keywords else "None"
        
        prompt = f"""
<systemMessage>
Plan a blog post structure for: {topic}
Keywords: {keywords_str}

Create 5 sections with headings. Respond with JSON only:
{{
    "title": "Your Blog Title",
    "intro": "Introduction overview",
    "sections": [
        {{"heading": "Section 1", "description": "What to cover"}},
        {{"heading": "Section 2", "description": "What to cover"}},
        {{"heading": "Section 3", "description": "What to cover"}},
        {{"heading": "Section 4", "description": "What to cover"}},
        {{"heading": "Section 5", "description": "What to cover"}}
    ]
}}

RESPOND WITH ONLY VALID JSON. NO OTHER TEXT.
</systemMessage>
"""
        return prompt
    
    def _parse_plan_response(self, response: str) -> BlogPlan:
        """Parse and validate the LLM planning response"""
        # Remove markdown code blocks if present
        response = response.strip()
        response = re.sub(r'^```json\s*', '', response, flags=re.IGNORECASE)
        response = re.sub(r'^```\s*', '', response)
        response = re.sub(r'\s*```$', '', response)
        
        # Remove common preamble text
        response = re.sub(r'^(Here is the JSON|Here\'s the JSON|JSON response):\s*', '', response, flags=re.IGNORECASE)
        
        # Extract JSON from response
        json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', response, re.DOTALL)
        if not json_match:
            # Try more permissive pattern
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if not json_match:
            raise ValueError(f"No JSON object found in response. Response start: {response[:200]}...")
        
        json_str = json_match.group()
        
        try:
            plan_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON syntax: {e}. JSON string start: {json_str[:200]}...")
        
        # Validate required fields
        if 'title' not in plan_data:
            raise ValueError("Missing required field: title")
        if 'sections' not in plan_data:
            raise ValueError("Missing required field: sections")
        if not isinstance(plan_data['sections'], list):
            raise ValueError("sections must be a list")
        if len(plan_data['sections']) < 1:
            raise ValueError("Must have at least 1 section")
        
        # Validate each section has heading
        for i, section in enumerate(plan_data['sections']):
            if 'heading' not in section:
                raise ValueError(f"Section {i} missing required field: heading")
        
        # Use Pydantic to validate and create the plan
        try:
            plan = BlogPlan(**plan_data)
            return plan
        except Exception as e:
            raise ValueError(f"Pydantic validation failed: {e}")

