"""Itinerary and route models."""

from pydantic import BaseModel, Field
from models.attraction import Attraction
from models.meal import MealSlot


class RouteSegment(BaseModel):
    """Travel segment between two attractions."""

    from_name: str = Field(description="Origin attraction name")
    to_name: str = Field(description="Destination attraction name")
    from_lat: float = Field(description="Origin latitude")
    from_lng: float = Field(description="Origin longitude")
    to_lat: float = Field(description="Destination latitude")
    to_lng: float = Field(description="Destination longitude")
    distance_meters: int = Field(ge=0, description="Distance in meters")
    duration_minutes: int = Field(ge=0, description="Estimated travel time in minutes")
    travel_mode: str = Field(default="walking", description="Travel mode")


class DayPlan(BaseModel):
    """Plan for a single day of the trip."""

    day_number: int = Field(ge=1, description="Day number (1-based)")
    attractions: list[Attraction] = Field(description="Ordered list of attractions")
    meals: list[MealSlot] = Field(
        default_factory=list,
        description="Scheduled meals for the day",
    )
    route_segments: list[RouteSegment] = Field(
        default_factory=list,
        description="Route segments between attractions",
    )
    total_travel_minutes: int = Field(
        default=0,
        ge=0,
        description="Total travel time for the day",
    )
    total_visit_minutes: int = Field(
        default=0,
        ge=0,
        description="Total visit time for the day",
    )
    start_time: str = Field(default="09:00", description="Day start time")
    end_time: str = Field(default="", description="Estimated end time")


class Itinerary(BaseModel):
    """Complete travel itinerary for the trip."""

    city: str = Field(description="Target city")
    num_days: int = Field(ge=1, description="Number of days")
    days: list[DayPlan] = Field(description="Daily plans")
    total_attractions: int = Field(ge=0, description="Total attractions across all days")
    total_travel_minutes: int = Field(
        default=0,
        ge=0,
        description="Total travel time across all days",
    )
    summary: str = Field(default="", description="Brief itinerary summary")
