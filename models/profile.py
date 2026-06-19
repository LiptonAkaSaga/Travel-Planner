"""Travel personality profile model."""

from enum import Enum
from pydantic import BaseModel, Field


class TravelStyle(str, Enum):
    """Primary travel style."""

    CULTURAL = "cultural"
    ADVENTURE = "adventure"
    RELAXATION = "relaxation"
    FOODIE = "foodie"
    NIGHTLIFE = "nightlife"
    FAMILY = "family"
    BUDGET = "budget"
    LUXURY = "luxury"


class Pace(str, Enum):
    """Sightseeing pace preference."""

    RELAXED = "relaxed"  # 2-3 attractions per day
    MODERATE = "moderate"  # 4-5 attractions per day
    INTENSE = "intense"  # 6+ attractions per day


class BudgetLevel(str, Enum):
    """Budget level for the trip."""

    LOW = "low"  # Free/cheap attractions, street food
    MEDIUM = "medium"  # Mix of paid and free, casual dining
    HIGH = "high"  # Premium experiences, fine dining


class TravelProfile(BaseModel):
    """Complete travel personality profile generated from quiz answers."""

    style: TravelStyle = Field(description="Primary travel style")
    pace: Pace = Field(description="Preferred sightseeing pace")
    budget: BudgetLevel = Field(description="Budget level for the trip")
    budget_amount: float | None = Field(
        default=None,
        description="Numeric budget in PLN for the entire trip",
    )

    preferred_categories: list[str] = Field(
        description="Attraction categories the user prefers",
        min_length=1,
    )

    avoid_categories: list[str] = Field(
        default_factory=list,
        description="Attraction categories to avoid",
    )

    interests: list[str] = Field(
        description="Specific interests (e.g., history, architecture, street food)",
        min_length=1,
    )

    dietary_restrictions: list[str] = Field(
        default_factory=list,
        description="Dietary restrictions for restaurant recommendations",
    )

    meal_preferences: dict[str, int] = Field(
        default_factory=dict,
        description="Meal preferences: {breakfast: count, lunch: count, dinner: count} per day",
    )

    mobility_notes: str = Field(
        default="",
        description="Mobility considerations (e.g., prefers walking, needs accessibility)",
    )

    summary: str = Field(
        description="One-paragraph human-readable summary of the travel personality",
    )
