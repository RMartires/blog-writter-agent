import os
from dotenv import load_dotenv
from pathlib import Path

# Get the directory where this config.py file is located
BASE_DIR = Path(__file__).resolve().parent

# Load .env file from the project root (where config.py is located)
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path, override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# User will change this model manually as needed
OPENROUTER_MODEL = "openai/gpt-oss-20b:free"  # Free tier model
# openai/gpt-oss-20b:free
# deepseek/deepseek-chat-v3.1:free
# deepseek/deepseek-r1-0528-qwen3-8b:free
# qwen/qwen3-235b-a22b:free

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

# Browser Use Configuration
PLAYWRIGHT_BROWSERS_PATH = os.getenv("PLAYWRIGHT_BROWSERS_PATH", 
    "/media/mats/3c24094c-800b-4576-a390-d23a6d7a02291/workspace/test_ai_gen/browser_use/.playwright-browsers")
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
MAX_ARTICLES_TO_EXTRACT = 5  # Number of articles to extract from search
BROWSER_TIMEOUT = 120  # Browser operation timeout in seconds

# MongoDB Configuration
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "blog_researcher")
MONGO_COLLECTION_ARTICLES = "articles"
MONGO_COLLECTION_PLAN_JOBS = "plan_generation_jobs"
MONGO_COLLECTION_BLOG_JOBS = "blog_generation_jobs"

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

