from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, AIMessage
from typing import List, Union, Any, Optional
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenRouterLLM(ChatOpenAI):
    """
    Extended ChatOpenAI with rate limiting and automatic retry logic for OpenRouter
    """
    
    min_request_interval: float = 2.0
    max_retries: int = 3
    retry_delay: int = 20
    last_request_time: Optional[float] = None
    
    def __init__(
        self, 
        api_key: str, 
        model: str, 
        temperature: float = 0.7,
        min_request_interval: float = 20.0,
        max_retries: int = 3,
        retry_delay: int = 20,
        **kwargs
    ):
        """
        Initialize OpenRouter LLM wrapper
        
        Args:
            api_key: OpenRouter API key
            model: Model name to use
            temperature: Temperature for generation
            min_request_interval: Minimum seconds between requests (throttling)
            max_retries: Maximum number of retries on rate limit errors
            retry_delay: Seconds to wait before retrying on rate limit (429)
            **kwargs: Additional arguments passed to ChatOpenAI
        """
        # Initialize parent ChatOpenAI
        super().__init__(
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            model_name=model,
            temperature=temperature,
            max_retries=0, 
            **kwargs
        )
        
        # Store rate limiting config
        self.min_request_interval = min_request_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.last_request_time = None
    
    def _throttle(self):
        """Ensure minimum time between requests"""
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                sleep_time = self.min_request_interval - elapsed
                logger.info(f"⏱️  Throttling: waiting {sleep_time:.1f}s before next request")
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error (429)"""
        error_str = str(error)
        return "429" in error_str or "rate limit" in error_str.lower()
    
    def predict(self, text: str, **kwargs) -> str:
        """
        Generate a response with automatic retry on rate limit errors
        
        Args:
            text: The prompt to send to the LLM
            **kwargs: Additional arguments
            
        Returns:
            Generated text response
        """
        for attempt in range(self.max_retries):
            try:
                # Throttle to prevent hitting rate limits
                self._throttle()
                
                # Make the API call using parent class method
                response = super().predict(text, **kwargs)
                return response
                
            except Exception as e:
                if self._is_rate_limit_error(e):
                    if attempt < self.max_retries - 1:
                        logger.warning(
                            f"⚠️  Rate limit hit (429). Waiting {self.retry_delay}s before retry "
                            f"(attempt {attempt + 1}/{self.max_retries})..."
                        )
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error(f"❌ Rate limit exceeded after {self.max_retries} attempts")
                        raise
                else:
                    # Non-rate-limit error, raise immediately
                    logger.error(f"❌ API Error: {e}")
                    raise
        
        raise Exception("Max retries exceeded")
    
    def invoke(self, input: Any, **kwargs) -> Any:
        """
        Invoke the LLM with messages (for chain compatibility)
        
        Args:
            input: Input to send to LLM
            **kwargs: Additional arguments
            
        Returns:
            Response from LLM
        """
        for attempt in range(self.max_retries):
            try:
                # Throttle to prevent hitting rate limits
                self._throttle()
                
                # Make the API call using parent class method
                response = super().invoke(input, **kwargs)
                return response
                
            except Exception as e:
                if self._is_rate_limit_error(e):
                    if attempt < self.max_retries - 1:
                        logger.warning(
                            f"⚠️  Rate limit hit (429). Waiting {self.retry_delay}s before retry "
                            f"(attempt {attempt + 1}/{self.max_retries})..."
                        )
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error(f"❌ Rate limit exceeded after {self.max_retries} attempts")
                        raise
                else:
                    # Non-rate-limit error, raise immediately
                    logger.error(f"❌ API Error: {e}")
                    raise
        
        raise Exception("Max retries exceeded")
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """
        Override internal _generate method with retry logic
        This is what LangChain actually calls when using chains like LLMChain
        
        Args:
            messages: Messages to send to LLM
            stop: Stop sequences
            run_manager: Run manager for callbacks
            **kwargs: Additional arguments
            
        Returns:
            Generated response
        """
        for attempt in range(self.max_retries):
            try:
                # Throttle to prevent hitting rate limits
                self._throttle()
                
                # Make the API call using parent class method
                response = super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
                return response
                
            except Exception as e:
                if self._is_rate_limit_error(e):
                    if attempt < self.max_retries - 1:
                        logger.warning(
                            f"⚠️  Rate limit hit (429). Waiting {self.retry_delay}s before retry "
                            f"(attempt {attempt + 1}/{self.max_retries})..."
                        )
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error(f"❌ Rate limit exceeded after {self.max_retries} attempts")
                        raise
                else:
                    # Non-rate-limit error, raise immediately
                    logger.error(f"❌ API Error: {e}")
                    raise
        
        raise Exception("Max retries exceeded")

