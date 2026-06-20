"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

# LLM settings — OpenAI-compatible (mimo)
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
OPENAI_MODEL: str = "mimo-v2.5-pro"

# LLM settings — Gemini
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = "gemini-3.5-flash"

# Available models for user selection
AVAILABLE_MODELS: dict[str, dict[str, str]] = {
    "mimo": {
        "label": "Mimo v2.5 Pro",
        "provider": "openai",
        "model": OPENAI_MODEL,
    },
    "gemini": {
        "label": "Gemini 3.5 Flash",
        "provider": "google",
        "model": GEMINI_MODEL,
    },
}

# Google Maps settings
DEFAULT_SEARCH_RADIUS_METERS: int = 5000
MAX_ATTRACTIONS_PER_DAY: int = 6
MIN_ATTRACTIONS_PER_DAY: int = 2

# Travel time estimates (minutes)
WALKING_SPEED_KMH: float = 4.0
TRANSIT_SPEED_KMH: float = 20.0
DRIVING_SPEED_KMH: float = 40.0

# Default visit durations (minutes) by category
DEFAULT_VISIT_DURATION: int = 60
CATEGORY_DURATIONS: dict[str, int] = {
    "museum": 90,
    "park": 60,
    "restaurant": 60,
    "landmark": 45,
    "church": 30,
    "shopping": 60,
    "viewpoint": 30,
    "entertainment": 120,
}

# Validation
MAX_RETRIES: int = 2
MAX_DAILY_HOURS: float = 10.0
START_HOUR: int = 9
END_HOUR: int = 21
