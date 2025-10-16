import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# User will change this model manually as needed
OPENROUTER_MODEL = "openai/gpt-oss-20b:free"  # Free tier model

# Iteration and Scoring Configuration
MAX_ITERATIONS = 2  # Maximum number of write-score-rewrite cycles
MIN_SCORE_THRESHOLD = 80  # Stop if this score is reached (0-100)
SAVE_ALL_ITERATIONS = True  # If True, save all iteration versions; if False, save only final
VERBOSE_OUTPUT = True  # Show detailed scoring feedback during iterations

# Score Category Weights (must sum to 1.0)
SCORE_WEIGHTS = {
    "readability": 0.25,
    "seo_optimization": 0.25,
    "content_quality": 0.20,
    "engagement": 0.15,
    "structure_format": 0.15
}

# Rate Limiting Configuration
API_MIN_REQUEST_INTERVAL = 5.0  # Minimum seconds between API requests (throttling)
API_MAX_RETRIES = 3  # Maximum number of retries on rate limit errors
API_RETRY_DELAY = 20  # Seconds to wait before retrying on 429 rate limit error

