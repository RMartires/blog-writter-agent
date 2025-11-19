from typing import List, Dict
import textstat
import re
import json
from pydantic import BaseModel, Field
from agents.lib.openrouter_wrapper import OpenRouterLLM
import config


# Define Pydantic models for structured output
class CategoryScore(BaseModel):
    """Score and feedback for a single category"""
    score: int = Field(..., description="Score for this category")
    feedback: str = Field(..., description="Specific feedback for this category")


class BlogScoringResponse(BaseModel):
    """Complete structured response for blog scoring"""
    readability: CategoryScore = Field(..., description="Readability score (0-25)")
    seo_optimization: CategoryScore = Field(..., description="SEO optimization score (0-25)")
    content_quality: CategoryScore = Field(..., description="Content quality score (0-20)")
    engagement: CategoryScore = Field(..., description="Engagement score (0-15)")
    structure_format: CategoryScore = Field(..., description="Structure & format score (0-15)")
    improvement_suggestions: List[str] = Field(
        ..., 
        min_length=5,
        max_length=5,
        description="Exactly 5 concrete, actionable suggestions"
    )


class BlogScorer:
    """Agent responsible for scoring blog posts on quality and SEO parameters"""
    
    def __init__(self, openrouter_api_key: str, model: str, session_id: str = None):
        """
        Initialize scorer agent with OpenRouter credentials
        
        Args:
            openrouter_api_key: OpenRouter API key
            model: Model name to use for scoring
            session_id: Optional session ID for trace grouping
        """
        if not openrouter_api_key:
            raise ValueError("OpenRouter API key is required")
        
        # Use wrapper with rate limiting and retry logic
        self.llm = OpenRouterLLM(
            api_key=openrouter_api_key,
            model=model,
            temperature=0.3,  # Lower temperature for more consistent scoring
            agent_name="ScorerAgent",
            session_id=session_id,
            min_request_interval=config.API_MIN_REQUEST_INTERVAL,
            max_retries=config.API_MAX_RETRIES,
            retry_delay=config.API_RETRY_DELAY,
            fallback_models=config.OPENROUTER_FALLBACK_MODELS
        )
        
        # Structured output not reliably supported with OpenRouter wrapper
        # Using JSON parsing with strict validation instead
        self.structured_llm = None
        print("ℹ️  Using JSON parsing with strict validation for scoring")
    
    def score_blog(
        self, 
        blog_content: str, 
        topic: str, 
        target_keywords: List[str]
    ) -> Dict:
        """
        Score a blog post across 5 categories using LLM-based evaluation
        
        Args:
            blog_content: The blog post content to score
            topic: The blog topic
            target_keywords: List of target keywords for SEO optimization
            
        Returns:
            Dictionary containing scores, feedback, and improvement suggestions
            
        Raises:
            Exception: If unable to get valid scoring after all retry attempts
        """
        # Calculate rule-based metrics first
        metrics = self._calculate_metrics(blog_content, target_keywords)
        
        # Create scoring prompt
        prompt = self._create_scoring_prompt(blog_content, topic, target_keywords, metrics)
        
        # Try multiple strategies to get structured output
        max_attempts = 5
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                # Use JSON parsing with strict validation
                print(f"🎯 Attempt {attempt + 1}/{max_attempts}: Using JSON parsing...")
                response = self.llm.invoke(prompt)
                
                # Extract content from response
                response_content = response.content if hasattr(response, 'content') else str(response)
                
                # Debug: show first part of response
                response_preview = response_content[:150].replace('\n', ' ')
                print(f"   Response preview: {response_preview}...")
                
                scores = self._parse_scoring_response(response_content, metrics)
                print(f"✅ Successfully scored with JSON parsing")
                return scores
                    
            except Exception as e:
                last_error = e
                error_msg = str(e)[:200]  # Truncate long error messages
                print(f"❌ Attempt {attempt + 1}/{max_attempts} failed: {error_msg}")
                
                if attempt < max_attempts - 1:
                    # Retry with progressively simpler prompts
                    if attempt == 0:
                        print("🔄 Retrying with same prompt...")
                    elif attempt == 1:
                        print("🔄 Retrying with simplified prompt...")
                        prompt = self._create_simplified_prompt(blog_content, topic, target_keywords, metrics)
                    elif attempt == 2:
                        print("🔄 Retrying with ultra-simple prompt...")
                        prompt = self._create_ultra_simple_prompt(blog_content, metrics)
                    else:
                        print(f"🔄 Final retry with ultra-simple prompt...")
        
        # If we get here, all attempts failed - raise exception instead of returning defaults
        raise Exception(
            f"Failed to get valid scoring response after {max_attempts} attempts. "
            f"Last error: {last_error}"
        )
    
    def _calculate_metrics(self, blog_content: str, target_keywords: List[str]) -> Dict:
        """Calculate rule-based metrics for the blog"""
        word_count = self.count_words(blog_content)
        flesch_score = self.calculate_flesch_score(blog_content)
        headings = self.extract_headings(blog_content)
        keyword_density = self.calculate_keyword_density(blog_content, target_keywords)
        
        return {
            "word_count": word_count,
            "flesch_score": flesch_score,
            "heading_count": len(headings),
            "headings": headings,
            "keyword_density": keyword_density
        }
    
    def _create_scoring_prompt(
        self, 
        blog_content: str, 
        topic: str, 
        target_keywords: List[str],
        metrics: Dict
    ) -> str:
        """Create the scoring prompt for the LLM"""
        keywords_str = ", ".join([f"'{kw}'" for kw in target_keywords]) if target_keywords else "None provided"
        
        prompt = f"""You are an expert blog content evaluator. You must respond ONLY with valid JSON, no other text.

BLOG TOPIC: {topic}
TARGET KEYWORDS: {keywords_str}

CALCULATED METRICS:
- Word Count: {metrics['word_count']} (optimal: 1000-1500)
- Flesch Reading Ease: {metrics['flesch_score']:.1f} (60-70 is optimal)
- Keyword Density: {metrics['keyword_density']:.2f}% (optimal: 1-3%)
- Number of Headings: {metrics['heading_count']}

BLOG CONTENT:
{blog_content}

---

EVALUATE AND SCORE THE BLOG ON THESE 5 CATEGORIES:

1. READABILITY (Max: 25 points)
   - Sentence clarity and variety (simple, compound, complex)
   - Paragraph structure (not too long)
   - Smooth transitions between sections
   - Use of active voice
   - Consider Flesch score as supporting data

2. SEO OPTIMIZATION (Max: 25 points)
   - Target keywords in title and headings (H2, H3)
   - Natural keyword integration throughout content
   - Keyword density (1-3% is optimal)
   - Proper heading hierarchy (H1 → H2 → H3)
   - Use of semantic/related keywords

3. CONTENT QUALITY (Max: 20 points)
   - Comprehensive topic coverage
   - Use of specific examples and data
   - Logical flow and coherence
   - Depth of information
   - Accuracy and credibility

4. ENGAGEMENT (Max: 15 points)
   - Strong hook in opening paragraph
   - Storytelling elements or compelling narratives
   - Use of questions, lists, or bullet points
   - Call-to-action present and clear
   - Overall reader appeal

5. STRUCTURE & FORMAT (Max: 15 points)
   - Appropriate word count (1000-1500 optimal)
   - Proper markdown formatting
   - Clear section divisions
   - Good visual hierarchy
   - Logical organization

RESPONSE FORMAT (JSON):
{{
    "readability": {{
        "score": <0-25>,
        "feedback": "<specific feedback on readability issues or strengths>"
    }},
    "seo_optimization": {{
        "score": <0-25>,
        "feedback": "<specific feedback on SEO aspects>"
    }},
    "content_quality": {{
        "score": <0-20>,
        "feedback": "<specific feedback on content depth and quality>"
    }},
    "engagement": {{
        "score": <0-15>,
        "feedback": "<specific feedback on reader engagement>"
    }},
    "structure_format": {{
        "score": <0-15>,
        "feedback": "<specific feedback on structure and formatting>"
    }},
    "improvement_suggestions": [
        "<concrete, actionable suggestion 1>",
        "<concrete, actionable suggestion 2>",
        "<concrete, actionable suggestion 3>",
        "<concrete, actionable suggestion 4>",
        "<concrete, actionable suggestion 5>"
    ]
}}

CRITICAL: Your response must be ONLY valid JSON. Do not include any explanatory text, markdown formatting, or code blocks. Start your response with {{ and end with }}."""

        return prompt
    
    def _create_simplified_prompt(
        self, 
        blog_content: str, 
        topic: str, 
        target_keywords: List[str],
        metrics: Dict
    ) -> str:
        """Create a simplified prompt that's more likely to get valid JSON"""
        keywords_str = ", ".join([f"'{kw}'" for kw in target_keywords]) if target_keywords else "None"
        
        # Truncate blog content if too long
        max_content_length = 3000
        if len(blog_content) > max_content_length:
            blog_content = blog_content[:max_content_length] + "...[truncated]"
        
        prompt = f"""
<systemMessage>        
Score this blog post. Topic: {topic}. Keywords: {keywords_str}

Metrics: Word Count={metrics['word_count']}, Flesch={metrics['flesch_score']:.1f}, Keyword Density={metrics['keyword_density']:.2f}%

Blog Content:
{blog_content}

---

Provide scores as JSON:
{{
    "readability": {{"score": 0-25, "feedback": "text"}},
    "seo_optimization": {{"score": 0-25, "feedback": "text"}},
    "content_quality": {{"score": 0-20, "feedback": "text"}},
    "engagement": {{"score": 0-15, "feedback": "text"}},
    "structure_format": {{"score": 0-15, "feedback": "text"}},
    "improvement_suggestions": ["suggestion1", "suggestion2", "suggestion3", "suggestion4", "suggestion5"]
}}

RESPOND WITH ONLY VALID JSON. NO OTHER TEXT.
</systemMessage>
"""
        
        return prompt
    
    def _create_ultra_simple_prompt(self, blog_content: str, metrics: Dict) -> str:
        """Ultra-simple prompt as last resort"""
        # Very short content sample
        content_sample = blog_content[:1000] + "..." if len(blog_content) > 1000 else blog_content
        
        prompt = f"""       
<systemMessage>        
Rate this blog content with JSON only:

{content_sample}

Required JSON format:
{{
    "readability": {{"score": 20, "feedback": "Good clarity"}},
    "seo_optimization": {{"score": 20, "feedback": "Keywords present"}},
    "content_quality": {{"score": 15, "feedback": "Informative"}},
    "engagement": {{"score": 12, "feedback": "Engaging"}},
    "structure_format": {{"score": 12, "feedback": "Well structured"}},
    "improvement_suggestions": ["tip1", "tip2", "tip3", "tip4", "tip5"]
}}

Respond ONLY with valid JSON matching this exact structure.
</systemMessage>
"""
        
        return prompt
    
    def _format_structured_response(self, response: BlogScoringResponse, metrics: Dict) -> Dict:
        """Format Pydantic model response into our expected dict format"""
        total_score = (
            response.readability.score +
            response.seo_optimization.score +
            response.content_quality.score +
            response.engagement.score +
            response.structure_format.score
        )
        
        return {
            "total_score": total_score,
            "category_scores": {
                "readability": {"score": response.readability.score, "max": 25},
                "seo_optimization": {"score": response.seo_optimization.score, "max": 25},
                "content_quality": {"score": response.content_quality.score, "max": 20},
                "engagement": {"score": response.engagement.score, "max": 15},
                "structure_format": {"score": response.structure_format.score, "max": 15}
            },
            "feedback": {
                "readability": response.readability.feedback,
                "seo_optimization": response.seo_optimization.feedback,
                "content_quality": response.content_quality.feedback,
                "engagement": response.engagement.feedback,
                "structure_format": response.structure_format.feedback
            },
            "improvement_suggestions": response.improvement_suggestions,
            "passes_threshold": False,  # Will be set by iteration manager
            "metrics": metrics
        }
    
    def _parse_scoring_response(self, response: str, metrics: Dict) -> Dict:
        """Parse the LLM scoring response with strict validation"""
        # Remove markdown code blocks if present
        response = response.strip()
        response = re.sub(r'^```json\s*', '', response, flags=re.IGNORECASE)
        response = re.sub(r'^```\s*', '', response)
        response = re.sub(r'\s*```$', '', response)
        
        # Remove common preamble text that LLMs sometimes add
        response = re.sub(r'^(Here is the JSON|Here\'s the JSON|JSON response):\s*', '', response, flags=re.IGNORECASE)
        
        # Extract JSON from response - look for the outermost braces
        json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', response, re.DOTALL)
        if not json_match:
            # Try a more permissive pattern for nested JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if not json_match:
            raise ValueError(f"No JSON object found in response. Response start: {response[:200]}...")
        
        json_str = json_match.group()
        
        try:
            scores_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON syntax: {e}. JSON string start: {json_str[:200]}...")
        
        # Strict validation of required fields
        required_fields = ['readability', 'seo_optimization', 'content_quality', 'engagement', 'structure_format']
        for field in required_fields:
            if field not in scores_data:
                raise ValueError(f"Missing required field: {field}")
            if 'score' not in scores_data[field]:
                raise ValueError(f"Missing score in {field}")
            if 'feedback' not in scores_data[field]:
                raise ValueError(f"Missing feedback in {field}")
            
            # Validate score is an integer
            if not isinstance(scores_data[field]['score'], int):
                raise ValueError(f"Score in {field} must be an integer, got {type(scores_data[field]['score'])}")
        
        if 'improvement_suggestions' not in scores_data:
            raise ValueError("Missing improvement_suggestions")
        
        if not isinstance(scores_data['improvement_suggestions'], list):
            raise ValueError("improvement_suggestions must be a list")
        
        # Calculate total score
        total_score = (
            scores_data['readability']['score'] +
            scores_data['seo_optimization']['score'] +
            scores_data['content_quality']['score'] +
            scores_data['engagement']['score'] +
            scores_data['structure_format']['score']
        )
        
        # Build structured result
        result = {
            "total_score": total_score,
            "category_scores": {
                "readability": {"score": scores_data['readability']['score'], "max": 25},
                "seo_optimization": {"score": scores_data['seo_optimization']['score'], "max": 25},
                "content_quality": {"score": scores_data['content_quality']['score'], "max": 20},
                "engagement": {"score": scores_data['engagement']['score'], "max": 15},
                "structure_format": {"score": scores_data['structure_format']['score'], "max": 15}
            },
            "feedback": {
                "readability": scores_data['readability']['feedback'],
                "seo_optimization": scores_data['seo_optimization']['feedback'],
                "content_quality": scores_data['content_quality']['feedback'],
                "engagement": scores_data['engagement']['feedback'],
                "structure_format": scores_data['structure_format']['feedback']
            },
            "improvement_suggestions": scores_data['improvement_suggestions'],
            "passes_threshold": False,  # Will be set by iteration manager
            "metrics": metrics
        }
        
        return result
    
    # Utility methods
    
    @staticmethod
    def count_words(text: str) -> int:
        """Count words in text"""
        # Remove markdown formatting for accurate count
        clean_text = re.sub(r'[#*`\[\]()]', '', text)
        words = clean_text.split()
        return len(words)
    
    @staticmethod
    def calculate_flesch_score(text: str) -> float:
        """Calculate Flesch Reading Ease score"""
        try:
            # Remove markdown formatting
            clean_text = re.sub(r'[#*`\[\]()]', '', text)
            score = textstat.flesch_reading_ease(clean_text)
            return score
        except Exception as e:
            print(f"Error calculating Flesch score: {e}")
            return 0.0
    
    @staticmethod
    def extract_headings(markdown: str) -> List[str]:
        """Extract all headings from markdown"""
        heading_pattern = r'^#{1,6}\s+(.+)$'
        headings = re.findall(heading_pattern, markdown, re.MULTILINE)
        return headings
    
    @staticmethod
    def calculate_keyword_density(text: str, keywords: List[str]) -> float:
        """Calculate keyword density as percentage"""
        if not keywords:
            return 0.0
        
        # Clean text
        clean_text = re.sub(r'[#*`\[\]()]', '', text.lower())
        total_words = len(clean_text.split())
        
        if total_words == 0:
            return 0.0
        
        # Count keyword occurrences
        keyword_count = 0
        for keyword in keywords:
            keyword_lower = keyword.lower()
            keyword_count += clean_text.count(keyword_lower)
        
        density = (keyword_count / total_words) * 100
        return density

