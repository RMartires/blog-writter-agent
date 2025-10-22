import os
import uuid
import asyncio
from typing import List, Dict, Optional
from browser_use import Agent, BrowserSession, Controller
from browser_use.browser import BrowserProfile
from browser_use.llm import ChatOpenRouter
from lmnr import Laminar, Instruments
from pydantic import BaseModel, Field
import traceback
import logging

from .models import ArticlePlan, ArticleSection, ArticleSubSection
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Laminar.initialize(project_api_key=os.getenv('LMNR_PROJECT_API_KEY'), disable_batch=True, disabled_instruments={Instruments.BROWSER_USE})


class SearchResult(BaseModel):
    """Search result from Google"""
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    snippet: Optional[str] = Field(None, description="Search snippet")


class SearchResults(BaseModel):
    """Collection of search results"""
    results: List[SearchResult] = Field(..., description="List of search results")


class ExtractedArticle(BaseModel):
    """Extracted article structure"""
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Source URL")
    intro: Optional[str] = Field(None, description="Introduction text")
    sections: List[ArticleSection] = Field(..., description="Article sections")
    raw_html_body: Optional[str] = Field(None, description="Raw HTML body content for complete context")
    full_html: Optional[str] = Field(None, description="Complete HTML document including head and body")


class ResearchAgentV2:
    """Agent responsible for web research using browser automation"""
    
    def __init__(self, api_key: str, playwright_path: Optional[str] = None):
        """Initialize the research agent with OpenRouter API key"""
        if not api_key:
            raise ValueError("OpenRouter API key is required")
        
        self.api_key = api_key
        self.playwright_path = playwright_path or config.PLAYWRIGHT_BROWSERS_PATH
        self.controller = Controller()
        
        # Initialize LLM
        self.llm = ChatOpenRouter(
            model=config.OPENROUTER_MODEL,
            api_key=api_key,
            temperature=0.7,
        )
        
        # Set environment variable for playwright browsers path
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = self.playwright_path
    
    def find_chrome(self) -> Optional[str]:
        """Find Chrome binary in the playwright browsers path"""
        base_dir = self.playwright_path
        if not os.path.exists(base_dir):
            logger.warning(f"Playwright browsers path does not exist: {base_dir}")
            return None
            
        for name in os.listdir(base_dir):
            if name.startswith("chromium-"):
                chrome_path = os.path.join(base_dir, name, 'chrome-linux', 'chrome')
                if os.path.exists(chrome_path):
                    return chrome_path
        return None
    
    async def search_and_extract_articles(self, query: str, max_articles: int = 5) -> List[ArticlePlan]:
        """
        Search Google for articles and extract their content
        
        Args:
            query: Search query string
            max_articles: Maximum number of articles to extract
            
        Returns:
            List of ArticlePlan objects with extracted content
        """
        try:
            logger.info(f"Starting search for: {query}")
            
            # Step 1: Search Google for articles
            search_results = await self._search_google(query, max_articles)
            
            if not search_results:
                logger.warning("No search results found")
                return []
            
            logger.info(f"Found {len(search_results)} search results")
            
            # Step 2: Extract content from each article
            article_plans = []
            for i, result in enumerate(search_results, 1):
                try:
                    logger.info(f"Extracting article {i}/{len(search_results)}: {result.title}")
                    article_plan = await self._extract_article_structure(result.url, result.title)
                    if article_plan:
                        article_plans.append(article_plan)
                        logger.info(f"Successfully extracted: {article_plan.title}")
                    else:
                        logger.warning(f"Failed to extract content from: {result.url}")
                except Exception as e:
                    logger.error(f"Error extracting article {result.url}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(article_plans)} articles")
            return article_plans
            
        except Exception as e:
            logger.error(f"Error in search_and_extract_articles: {e}")
            traceback.print_exc()
            return []
    
    async def _search_google(self, query: str, max_results: int) -> List[SearchResult]:
        """Search Google and extract article URLs"""
        task = f'''
        Goal: Search Google for "{query}" and extract the top {max_results} results url
        - Navigate to Google
        - Enter the search query "{query}" and search
        - Wait for results to load
        - Extract the top {max_results} organic result URLs (skip ads and sponsored results)
        - For each result, extract the title, URL, and snippet
        - Make sure to keep the entire url in the result not just the domain
        - Scroll if top results are not web page links, the goal is to scroll the page untill we get a list of web page urls
        - Do not inclde urls like youtube
        - Complete when URLs are extracted
        - Do not open another tab, use only one tab
        '''
        
        logger.info(f"Searching Google for: {query}")
        
        # Create unique profile directory
        unique_profile = f"./profiles/search-{uuid.uuid4().hex[:8]}"
        os.makedirs(os.path.dirname(unique_profile), exist_ok=True)
        
        # Find Chrome binary
        chrome_bin = self.find_chrome()
        if not chrome_bin:
            raise RuntimeError("Chrome binary not found in playwright browsers path")
        
        # Create browser profile
        bp = BrowserProfile(
            viewport_size={'width': 1280, 'height': 720},
            user_data_dir=unique_profile,
            executable_path=chrome_bin,
            headless=config.BROWSER_HEADLESS,
            chromium_sandbox=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        
        # Create agent
        agent = Agent(
            task=task,
            llm=self.llm,
            browser_profile=bp,
            controller=self.controller,
            output_model_schema=SearchResults,
            llm_timeout=config.BROWSER_TIMEOUT
        )
        
        try:
            history = await agent.run()
            result = history.final_result()
            
            if result:
                parsed_results = SearchResults.model_validate_json(result)
                logger.info(f"Found {len(parsed_results.results)} search results")
                return parsed_results.results
            else:
                logger.warning("No search results returned")
                return []
                
        except Exception as e:
            logger.error(f"Error during Google search: {e}")
            traceback.print_exc()
            return []
    
    async def _extract_article_structure(self, url: str, title: str) -> Optional[ArticlePlan]:
        """Extract article structure and content from a URL"""
        task = f'''
        Goal: Extract complete article content from url={url}
        - Navigate to the article URL
        - Wait for page to fully load (including JavaScript and dynamic content)
        - Execute JavaScript to capture the entire HTML body: document.body.innerHTML
        - Execute JavaScript to capture the complete page HTML: document.documentElement.outerHTML
        - Scroll the entire page to ensure all content is loaded and visible
        - Extract all text content from the page including headers, paragraphs, lists, and any other text elements
        - Identify the main article title (H1)
        - Create a structure of all the text related to the article
        - Return structured data with all text from the blog content
        - Make sure to extract the complete text content, not just summaries, full raw text
        - IMPORTANT: Include the raw HTML body content in the raw_html_body field for complete context
        - IMPORTANT: Include the full HTML document in the full_html field
        - Use JavaScript evaluation to get: document.body.innerHTML and document.documentElement.outerHTML
        - Do not open another tab, use only one tab
        '''
        
        logger.info(f"Extracting article structure from: {url}")
        
        # Create unique profile directory
        unique_profile = f"./profiles/extract-{uuid.uuid4().hex[:8]}"
        os.makedirs(os.path.dirname(unique_profile), exist_ok=True)
        
        # Find Chrome binary
        chrome_bin = self.find_chrome()
        if not chrome_bin:
            raise RuntimeError("Chrome binary not found in playwright browsers path")
        
        # Create browser profile
        bp = BrowserProfile(
            viewport_size={'width': 1280, 'height': 720},
            user_data_dir=unique_profile,
            executable_path=chrome_bin,
            headless=config.BROWSER_HEADLESS,
            chromium_sandbox=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        
        # Create agent
        agent = Agent(
            task=task,
            llm=self.llm,
            browser_profile=bp,
            controller=self.controller,
            output_model_schema=ExtractedArticle,
            llm_timeout=config.BROWSER_TIMEOUT,
            step_timeout=60,  # Increased timeout for HTML capture
            use_vision=False,  # Disable vision to focus on text content
            include_attributes=['id', 'class', 'data-*', 'href', 'src']  # Include more attributes for better context
        )
        
        try:
            history = await agent.run()
            result = history.final_result()
            
            if result:
                parsed_article = ExtractedArticle.model_validate_json(result)
                
                # Log HTML capture information
                if parsed_article.raw_html_body:
                    logger.info(f"Captured HTML body: {len(parsed_article.raw_html_body)} characters")
                if parsed_article.full_html:
                    logger.info(f"Captured full HTML: {len(parsed_article.full_html)} characters")
                
                # Convert to ArticlePlan format
                article_plan = ArticlePlan(
                    title=parsed_article.title,
                    url=url,
                    intro=parsed_article.intro,
                    sections=parsed_article.sections
                )
                
                logger.info(f"Successfully extracted article: {article_plan.title}")
                return article_plan
            else:
                logger.warning(f"No content extracted from: {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting article from {url}: {e}")
            traceback.print_exc()
            return None

