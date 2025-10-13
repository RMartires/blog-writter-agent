from typing import List, Dict
import textstat
import re
import json
from agents.lib.openrouter_wrapper import OpenRouterLLM
import config


class BlogScorer:
    """Agent responsible for scoring blog posts on quality and SEO parameters"""
    
    def __init__(self, openrouter_api_key: str, model: str):
        """
        Initialize scorer agent with OpenRouter credentials
        
        Args:
            openrouter_api_key: OpenRouter API key
            model: Model name to use for scoring
        """
        if not openrouter_api_key:
            raise ValueError("OpenRouter API key is required")
        
        # Use wrapper with rate limiting and retry logic
        self.llm = OpenRouterLLM(
            api_key=openrouter_api_key,
            model=model,
            temperature=0.3,  # Lower temperature for more consistent scoring
            min_request_interval=config.API_MIN_REQUEST_INTERVAL,
            max_retries=config.API_MAX_RETRIES,
            retry_delay=config.API_RETRY_DELAY
        )
    
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
        """
        # Calculate rule-based metrics first
        metrics = self._calculate_metrics(blog_content, target_keywords)
        
        # Create scoring prompt
        prompt = self._create_scoring_prompt(blog_content, topic, target_keywords, metrics)
        
        # Get LLM scoring
        try:
            response = self.llm.invoke(prompt)
            scores = self._parse_scoring_response(response, metrics)
            return scores
        except Exception as e:
            print(f"Error during scoring: {e}")
            # Return default scores if LLM fails
            return self._default_scores(metrics)
    
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
        
        prompt = f"""
<systemMessage>        
You are an expert blog content evaluator. Score this blog post across 5 categories.

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

Provide ONLY the JSON response, no additional text.
</systemMessage>
"""

        return prompt
    
    def _parse_scoring_response(self, response: str, metrics: Dict) -> Dict:
        """Parse the LLM scoring response into structured format"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                scores_data = json.loads(json_match.group())
            else:
                scores_data = json.loads(response)
            
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
                    "readability": {
                        "score": scores_data['readability']['score'],
                        "max": 25
                    },
                    "seo_optimization": {
                        "score": scores_data['seo_optimization']['score'],
                        "max": 25
                    },
                    "content_quality": {
                        "score": scores_data['content_quality']['score'],
                        "max": 20
                    },
                    "engagement": {
                        "score": scores_data['engagement']['score'],
                        "max": 15
                    },
                    "structure_format": {
                        "score": scores_data['structure_format']['score'],
                        "max": 15
                    }
                },
                "feedback": {
                    "readability": scores_data['readability']['feedback'],
                    "seo_optimization": scores_data['seo_optimization']['feedback'],
                    "content_quality": scores_data['content_quality']['feedback'],
                    "engagement": scores_data['engagement']['feedback'],
                    "structure_format": scores_data['structure_format']['feedback']
                },
                "improvement_suggestions": scores_data.get('improvement_suggestions', []),
                "passes_threshold": False,  # Will be set by iteration manager
                "metrics": metrics
            }
            
            return result
            
        except Exception as e:
            print(f"Error parsing scoring response: {e}")
            print(f"Response was: {response[:500]}...")
            return self._default_scores(metrics)
    
    def _default_scores(self, metrics: Dict) -> Dict:
        """Return default scores if LLM scoring fails"""
        return {
            "total_score": 50,
            "category_scores": {
                "readability": {"score": 12, "max": 25},
                "seo_optimization": {"score": 12, "max": 25},
                "content_quality": {"score": 10, "max": 20},
                "engagement": {"score": 8, "max": 15},
                "structure_format": {"score": 8, "max": 15}
            },
            "feedback": {
                "readability": "Unable to score - LLM error",
                "seo_optimization": "Unable to score - LLM error",
                "content_quality": "Unable to score - LLM error",
                "engagement": "Unable to score - LLM error",
                "structure_format": "Unable to score - LLM error"
            },
            "improvement_suggestions": ["Retry scoring with a different model"],
            "passes_threshold": False,
            "metrics": metrics
        }
    
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

