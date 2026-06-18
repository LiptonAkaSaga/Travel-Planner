"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

# LLM settings
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = "gpt-4o-mini"

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
