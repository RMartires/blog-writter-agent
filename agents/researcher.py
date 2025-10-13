from tavily import TavilyClient
from typing import List, Dict


class ResearchAgent:
    """Agent responsible for web research using Tavily API"""
    
    def __init__(self, api_key: str):
        """Initialize the research agent with Tavily API key"""
        if not api_key:
            raise ValueError("Tavily API key is required")
        self.client = TavilyClient(api_key=api_key)
    
    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search the web for relevant information using Tavily API
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing title, url, content, and score
        """
        try:
            response = self.client.search(
                query=query,
                search_depth="advanced",  # Deep search for comprehensive results
                max_results=max_results,
                include_answer=True,      # Get AI-generated answer summary
                include_raw_content=True  # Full content for RAG
            )
            
            return self._process_results(response)
        
        except Exception as e:
            print(f"Error during research: {e}")
            return []
    
    def _process_results(self, response: Dict) -> List[Dict]:
        """
        Process and clean search results from Tavily API
        
        Args:
            response: Raw response from Tavily API
            
        Returns:
            Cleaned list of research results
        """
        processed_results = []
        
        # Extract results from response
        results = response.get('results', [])
        
        for result in results:
            processed_results.append({
                'title': result.get('title', 'Untitled'),
                'url': result.get('url', ''),
                'content': result.get('content', '') or result.get('raw_content', ''),
                'score': result.get('score', 0.0)
            })
        
        # Filter out results with empty content
        processed_results = [r for r in processed_results if r['content'].strip()]
        
        return processed_results

