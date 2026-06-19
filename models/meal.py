"""Meal-related models for restaurant planning."""

from enum import Enum
from pydantic import BaseModel, Field


class MealType(str, Enum):
    """Type of meal."""

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"


# Meal time windows (hour ranges)
MEAL_WINDOWS: dict[MealType, tuple[int, int]] = {
    MealType.BREAKFAST: (7, 10),   # 7:00 - 10:00
    MealType.LUNCH: (12, 15),      # 12:00 - 15:00
    MealType.DINNER: (18, 21),     # 18:00 - 21:00
}

# Default meal durations (minutes)
MEAL_DURATIONS: dict[MealType, int] = {
    MealType.BREAKFAST: 45,
    MealType.LUNCH: 60,
    MealType.DINNER: 90,
}

# Meal type labels (Polish)
MEAL_LABELS: dict[MealType, str] = {
    MealType.BREAKFAST: "Śniadanie",
    MealType.LUNCH: "Obiad",
    MealType.DINNER: "Kolacja",
}

# Meal type icons
MEAL_ICONS: dict[MealType, str] = {
    MealType.BREAKFAST: "🍳",
    MealType.LUNCH: "🍲",
    MealType.DINNER: "🍽️",
}


class MealSlot(BaseModel):
    """A meal slot in the itinerary."""

    meal_type: MealType = Field(description="Type of meal")
    restaurant_name: str = Field(description="Restaurant name")
    restaurant_address: str = Field(default="", description="Restaurant address")
    place_id: str = Field(default="", description="Google Maps place ID")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Restaurant rating")
    price_level: int | None = Field(default=None, ge=0, le=4, description="Price level")
    duration_minutes: int = Field(default=60, ge=15, description="Meal duration")
    scheduled_time: str = Field(default="", description="Scheduled time HH:MM")
    lat: float = Field(default=0.0, description="Latitude")
    lng: float = Field(default=0.0, description="Longitude")
    description: str = Field(default="", description="Brief description")
