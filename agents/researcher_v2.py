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
        - make sure to keep the entire url in the result not just the domain
        - do not inclde urls like youtube
        - Complete when URLs are extracted
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
        - Identify the main article title (H1)
        - Extract all text from the page, the article will be long so make sure to scroll the entire page
        - Extract and read the entire web page
        - Figure out all sections like introduction/opening paragraphs (first few paragraphs before first H2)
        - Find all H2 section headings and their complete text content
        - For each H2 section, find any H3 subsections and their text content
        - Return structured data with headings and full text content
        - Make sure to extract the complete text content, not just summaries
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
            step_timeout=30
        )
        
        try:
            history = await agent.run()
            result = history.final_result()
            
            if result:
                parsed_article = ExtractedArticle.model_validate_json(result)
                
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

