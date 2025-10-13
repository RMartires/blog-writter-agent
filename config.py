import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# User will change this model manually as needed
OPENROUTER_MODEL = "deepseek/deepseek-r1:free"  # Free tier model

