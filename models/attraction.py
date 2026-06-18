"""Attraction data model."""

from pydantic import BaseModel, Field


class Attraction(BaseModel):
    """A real-world attraction retrieved from Google Maps."""

    place_id: str = Field(description="Google Maps place ID")
    name: str = Field(description="Attraction name")
    address: str = Field(default="", description="Formatted address")
    lat: float = Field(description="Latitude")
    lng: float = Field(description="Longitude")

    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Google rating")
    user_ratings_total: int = Field(default=0, ge=0, description="Number of ratings")

    categories: list[str] = Field(
        default_factory=list,
        description="Category tags (e.g., museum, park, restaurant)",
    )

    price_level: int | None = Field(
        default=None,
        ge=0,
        le=4,
        description="Google price level (0=free, 4=very expensive)",
    )

    opening_hours: dict[str, str] = Field(
        default_factory=dict,
        description="Opening hours by day of week",
    )

    visit_duration_minutes: int = Field(
        default=60,
        ge=15,
        description="Estimated visit duration in minutes",
    )

    description: str = Field(
        default="",
        description="Brief description of the attraction",
    )
