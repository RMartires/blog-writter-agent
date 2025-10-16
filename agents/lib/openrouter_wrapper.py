from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, AIMessage
from typing import List, Union, Any, Optional
import time
import logging
import uuid
from datetime import datetime
from langsmith import traceable
from pydantic import Field

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
    agent_name: str = Field(default="Unknown", description="Name of the agent using this LLM")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Session ID for grouping related calls")
    
    def __init__(
        self, 
        api_key: str, 
        model: str, 
        temperature: float = 0.7,
        min_request_interval: float = 2.0,
        max_retries: int = 3,
        retry_delay: int = 20,
        agent_name: str = "Unknown",
        session_id: str = None,
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
            agent_name: Name of the agent using this LLM (for LangSmith tracing)
            session_id: Optional session ID for grouping related calls
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
    
    @traceable(name="OpenRouterLLM.invoke")
    def invoke(self, input: Any, **kwargs) -> Any:
        """
        Invoke the LLM with messages (for chain compatibility) with LangSmith tracing
        
        Args:
            input: Input to send to LLM
            **kwargs: Additional arguments
            
        Returns:
            Response from LLM
        """
        # Add metadata for LangSmith tracing
        metadata = {
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "model": self.model_name,
            "temperature": self.temperature,
            "method": "invoke"
        }
        
        for attempt in range(self.max_retries):
            try:
                # Throttle to prevent hitting rate limits
                self._throttle()
                
                # Log the interaction start
                logger.info(f"🤖 {self.agent_name}: Starting LLM invoke call (attempt {attempt + 1})")
                
                # Make the API call using parent class method
                response = super().invoke(input, **kwargs)
                
                # Log successful completion
                logger.info(f"✅ {self.agent_name}: LLM invoke call completed successfully")
                return response
                
            except Exception as e:
                if self._is_rate_limit_error(e):
                    if attempt < self.max_retries - 1:
                        logger.warning(
                            f"⚠️  {self.agent_name}: Rate limit hit (429). Waiting {self.retry_delay}s before retry "
                            f"(attempt {attempt + 1}/{self.max_retries})..."
                        )
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error(f"❌ {self.agent_name}: Rate limit exceeded after {self.max_retries} attempts")
                        raise
                else:
                    # Non-rate-limit error, raise immediately
                    logger.error(f"❌ {self.agent_name}: API Error: {e}")
                    raise
        
        raise Exception("Max retries exceeded")
    
    @traceable(name="OpenRouterLLM._generate")
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """
        Override internal _generate method with retry logic and LangSmith tracing
        This is what LangChain actually calls when using chains like LLMChain
        
        Args:
            messages: Messages to send to LLM
            stop: Stop sequences
            run_manager: Run manager for callbacks
            **kwargs: Additional arguments
            
        Returns:
            Generated response
        """
        # Add metadata for LangSmith tracing
        metadata = {
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "model": self.model_name,
            "temperature": self.temperature,
            "method": "_generate"
        }
        
        for attempt in range(self.max_retries):
            try:
                # Throttle to prevent hitting rate limits
                self._throttle()
                
                # Log the interaction start
                logger.info(f"🤖 {self.agent_name}: Starting LLM call (attempt {attempt + 1})")
                
                # Make the API call using parent class method
                response = super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
                
                # Log successful completion
                logger.info(f"✅ {self.agent_name}: LLM call completed successfully")
                return response
                
            except Exception as e:
                if self._is_rate_limit_error(e):
                    if attempt < self.max_retries - 1:
                        logger.warning(
                            f"⚠️  {self.agent_name}: Rate limit hit (429). Waiting {self.retry_delay}s before retry "
                            f"(attempt {attempt + 1}/{self.max_retries})..."
                        )
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error(f"❌ {self.agent_name}: Rate limit exceeded after {self.max_retries} attempts")
                        raise
                else:
                    # Non-rate-limit error, raise immediately
                    logger.error(f"❌ {self.agent_name}: API Error: {e}")
                    raise
        
        raise Exception("Max retries exceeded")

