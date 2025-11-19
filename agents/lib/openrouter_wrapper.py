from langchain_openai import ChatOpenAI
from langchain.schema.runnable.config import RunnableConfig
from typing import List, Union, Any, Optional
import time
import logging
import uuid
import threading
from datetime import datetime, timedelta
from langsmith import traceable
from pydantic import Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelErrorTracker:
    """
    Thread-safe tracker for model error counts with automatic reset every 10 minutes.
    Used to select the best model (least errors) for fallback.
    """
    
    def __init__(self, reset_interval_minutes: int = 10):
        """
        Initialize the error tracker
        
        Args:
            reset_interval_minutes: How often to reset error counts (default: 10 minutes)
        """
        self._error_counts: dict[str, int] = {}
        self._error_timestamps: dict[str, list[float]] = {}  # Track when errors occurred
        self._lock = threading.Lock()
        self.reset_interval_seconds = reset_interval_minutes * 60
        self._last_reset_time = time.time()
    
    def record_error(self, model_name: str):
        """Record an error for a specific model"""
        with self._lock:
            current_time = time.time()
            
            # Initialize if needed
            if model_name not in self._error_counts:
                self._error_counts[model_name] = 0
                self._error_timestamps[model_name] = []
            
            # Record error with timestamp
            self._error_counts[model_name] += 1
            self._error_timestamps[model_name].append(current_time)
            
            logger.info(f"📊 Model error recorded: {model_name} (total errors: {self._error_counts[model_name]})")
            
            # Auto-reset old counts periodically
            self._reset_old_counts(current_time)
    
    def _reset_old_counts(self, current_time: float):
        """Reset error counts older than reset_interval"""
        # Check if it's time to reset (every reset_interval)
        if current_time - self._last_reset_time >= self.reset_interval_seconds:
            cutoff_time = current_time - self.reset_interval_seconds
            
            # Remove old timestamps and recalculate counts
            for model_name in list(self._error_timestamps.keys()):
                old_timestamps = self._error_timestamps[model_name]
                # Keep only recent errors (within reset_interval)
                recent_timestamps = [ts for ts in old_timestamps if ts >= cutoff_time]
                self._error_timestamps[model_name] = recent_timestamps
                self._error_counts[model_name] = len(recent_timestamps)
                
                # Remove models with zero errors
                if self._error_counts[model_name] == 0:
                    del self._error_counts[model_name]
                    del self._error_timestamps[model_name]
            
            self._last_reset_time = current_time
            logger.info(f"🔄 Model error counts reset (10-minute window)")
    
    def get_best_model(self, available_models: List[str]) -> Optional[str]:
        """
        Get the model with the least errors from the available models list.
        If no errors recorded, returns the first model in the list.
        
        Args:
            available_models: List of model names to choose from
            
        Returns:
            Model name with least errors, or first model if no errors recorded
        """
        with self._lock:
            current_time = time.time()
            self._reset_old_counts(current_time)
            
            if not available_models:
                return None
            
            # Find model with minimum error count
            best_model = available_models[0]
            min_errors = self._error_counts.get(best_model, 0)
            
            for model in available_models:
                error_count = self._error_counts.get(model, 0)
                if error_count < min_errors:
                    min_errors = error_count
                    best_model = model
            
            logger.info(f"🎯 Selected best model: {best_model} (errors: {min_errors})")
            return best_model
    
    def get_error_count(self, model_name: str) -> int:
        """Get current error count for a model"""
        with self._lock:
            return self._error_counts.get(model_name, 0)


# Global instance shared across all OpenRouterLLM instances
_global_error_tracker = ModelErrorTracker(reset_interval_minutes=10)

# Module-level variables for global throttling (not class-level to avoid pickling issues)
_global_last_request_time: Optional[float] = None
_global_throttle_lock = threading.Lock()


class OpenRouterLLM(ChatOpenAI):
    """
    Extended ChatOpenAI with rate limiting and automatic retry logic for OpenRouter.
    Features:
    - Global throttling across all instances
    - Automatic model fallback on rate limit errors
    - Model error tracking with 10-minute reset window
    """
    
    min_request_interval: float = 2.0
    max_retries: int = 3
    retry_delay: int = 20
    agent_name: str = Field(default="Unknown", description="Name of the agent using this LLM")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Session ID for grouping related calls")
    fallback_models: List[str] = Field(default_factory=list, description="List of fallback models for rate limit errors")
    
    # Private attributes (not serialized by Pydantic)
    _current_model: str = ""
    _error_tracker: Optional[Any] = None
    
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
        fallback_models: Optional[List[str]] = None,
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
            fallback_models: List of model names to try if current model hits rate limit
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
        
        # Store fallback models (include current model if not in list)
        fallback_list = fallback_models or [model]
        if model not in fallback_list:
            fallback_list.insert(0, model)
        self.fallback_models = fallback_list
        
        # Track current model being used
        object.__setattr__(self, '_current_model', model)
        
        # Reference to global error tracker (excluded from serialization)
        object.__setattr__(self, '_error_tracker', _global_error_tracker)
    
    def _throttle(self):
        """Ensure minimum time between requests using global throttling"""
        global _global_last_request_time, _global_throttle_lock
        with _global_throttle_lock:
            current_time = time.time()
            if _global_last_request_time is not None:
                elapsed = current_time - _global_last_request_time
                if elapsed < self.min_request_interval:
                    sleep_time = self.min_request_interval - elapsed
                    logger.info(f"⏱️  Global throttling: waiting {sleep_time:.1f}s before next request")
                    time.sleep(sleep_time)
                    current_time = time.time()
            
            _global_last_request_time = current_time
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error (429)"""
        error_str = str(error)
        error_type = type(error).__name__
        
        # Check exception attributes for status code (OpenAI SDK uses status_code)
        if hasattr(error, 'status_code') and error.status_code == 429:
            logger.info(f"🔍 Detected rate limit error via status_code: {error_type} - {error_str[:200]}")
            return True
        
        # Check response attribute if available
        if hasattr(error, 'response'):
            response = error.response
            if hasattr(response, 'status_code') and response.status_code == 429:
                logger.info(f"🔍 Detected rate limit error via response.status_code: {error_type} - {error_str[:200]}")
                return True
        
        # Check error string for rate limit indicators
        is_rate_limit = (
            "429" in error_str or 
            "rate limit" in error_str.lower() or
            "rate-limited" in error_str.lower() or
            "too many requests" in error_str.lower() or
            "rate_limit" in error_str.lower() or
            "rate limit exceeded" in error_str.lower()
        )
        
        # Also check error type (some HTTP libraries raise specific exceptions)
        if is_rate_limit:
            logger.info(f"🔍 Detected rate limit error: {error_type} - {error_str[:200]}")
            return True
        
        return False
    
    def _switch_model(self, new_model: str):
        """Switch to a different model"""
        current = getattr(self, '_current_model', '')
        if new_model == current:
            return
        
        logger.info(f"🔄 Switching model: {current} -> {new_model}")
        object.__setattr__(self, '_current_model', new_model)
        self.model_name = new_model
    
    def _execute_with_retry(self, execute_fn, method_name: str):
        """
        Execute a function with retry logic for rate limit errors.
        
        Args:
            execute_fn: Callable that executes the actual API call
            method_name: Name of the calling method (for logging)
            
        Returns:
            Result from execute_fn
        """
        max_total_attempts = self.max_retries * len(self.fallback_models)
        attempt_count = 0
        models_tried = set()
        
        while attempt_count < max_total_attempts:
            try:
                # Throttle to prevent hitting rate limits (global throttling)
                self._throttle()
                
                # Get current model (using getattr to handle private attribute)
                current_model = getattr(self, '_current_model', self.model_name)
                
                # Log the interaction start
                logger.info(
                    f"🤖 {self.agent_name}: Starting LLM {method_name} call "
                    f"(model: {current_model}, attempt {attempt_count + 1})"
                )
                
                # Execute the actual API call
                result = execute_fn()
                
                # Log successful completion
                logger.info(f"✅ {self.agent_name}: LLM {method_name} call completed successfully (model: {current_model})")
                return result
                
            except Exception as e:
                error_type = type(e).__name__
                error_str = str(e)
                logger.info(f"🔍 {self.agent_name}: Caught exception in {method_name}(): {error_type} - {error_str[:300]}")
                
                if self._is_rate_limit_error(e):
                    # Get current model and record error
                    current_model = getattr(self, '_current_model', self.model_name)
                    error_tracker = getattr(self, '_error_tracker', _global_error_tracker)
                    error_tracker.record_error(current_model)
                    models_tried.add(current_model)
                    
                    logger.info(f"📊 {self.agent_name}: Recorded error for {current_model}. Models tried so far: {models_tried}")
                    
                    # Try to extract reset time from error metadata
                    wait_time = self.retry_delay
                    try:
                        # Check if error has metadata with reset time
                        if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                            reset_header = e.response.headers.get('X-RateLimit-Reset')
                            if reset_header:
                                reset_timestamp = int(reset_header) / 1000  # Convert from milliseconds
                                current_time = time.time()
                                wait_time = max(1, reset_timestamp - current_time + 1)  # Add 1 second buffer
                                logger.info(f"⏰ {self.agent_name}: Parsed reset time from headers, waiting {wait_time:.1f}s")
                    except (AttributeError, ValueError, TypeError) as parse_error:
                        logger.debug(f"Could not parse reset time from error: {parse_error}")
                    
                    # Get best fallback model (least errors)
                    best_model = error_tracker.get_best_model(self.fallback_models)
                    logger.info(f"🎯 {self.agent_name}: Best fallback model selected: {best_model}")
                    
                    if best_model and best_model not in models_tried:
                        # Switch to best model and retry
                        self._switch_model(best_model)
                        logger.warning(
                            f"⚠️  {self.agent_name}: Rate limit hit (429) on {models_tried}. "
                            f"Switching to {best_model} and retrying (attempt {attempt_count + 1}/{max_total_attempts})..."
                        )
                        attempt_count += 1
                        # Small delay before retry with new model
                        time.sleep(2)
                        continue
                    elif attempt_count < max_total_attempts - 1:
                        # Try waiting and retrying with current model
                        logger.warning(
                            f"⚠️  {self.agent_name}: Rate limit hit (429). Waiting {wait_time:.1f}s before retry "
                            f"(attempt {attempt_count + 1}/{max_total_attempts})..."
                        )
                        time.sleep(wait_time)
                        attempt_count += 1
                        continue
                    else:
                        # All attempts exhausted
                        logger.error(
                            f"❌ {self.agent_name}: Rate limit exceeded after {max_total_attempts} attempts. "
                            f"Models tried: {models_tried}"
                        )
                        raise
                else:
                    # Non-rate-limit error, raise immediately
                    logger.error(f"❌ {self.agent_name}: Non-rate-limit API Error ({error_type}): {error_str[:200]}")
                    raise
        
        raise Exception(f"Max retries exceeded after trying {len(models_tried)} models")
    
    @traceable(name="OpenRouterLLM.invoke")
    def invoke(self, input: Any, **kwargs) -> Any:
        """
        Invoke the LLM with messages (for chain compatibility) with LangSmith tracing.
        Automatically switches to fallback models on rate limit errors.
        
        Args:
            input: Input to send to LLM
            **kwargs: Additional arguments
            
        Returns:
            Response from LLM
        """
        def execute():
            # Get current model for metadata
            current_model = getattr(self, '_current_model', self.model_name)
            
            # Update metadata with current model
            config = RunnableConfig(
                metadata = {
                    "agent_name": self.agent_name,
                    "session_id": self.session_id,
                    "model": current_model,
                    "temperature": self.temperature,
                    "method": "invoke"
                }
            )
            
            # Make the API call using parent class method
            return super(OpenRouterLLM, self).invoke(input, config=config)
        
        return self._execute_with_retry(execute, "invoke")
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """
        Override _generate to add retry logic for LLMChain calls.
        LLMChain calls _generate instead of invoke, so we need to wrap it.
        """
        logger.info(f"🔧 {self.agent_name}: _generate() called - applying retry logic")
        
        def execute():
            # Call parent's _generate method
            return super(OpenRouterLLM, self)._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        
        return self._execute_with_retry(execute, "_generate")
    
    def __call__(self, *args, **kwargs):
        """
        Override __call__ to ensure retry logic is used when LLMChain calls the LLM directly.
        This delegates to invoke() which has the retry/fallback logic.
        """
        logger.info(f"🔧 {self.agent_name}: __call__() intercepted (delegating to invoke)")
        return self.invoke(*args, **kwargs)
    
