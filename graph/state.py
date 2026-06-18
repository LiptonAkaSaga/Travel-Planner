"""LangGraph state definition for the travel planning workflow."""

from typing import TypedDict
from models.profile import TravelProfile
from models.attraction import Attraction
from models.itinerary import Itinerary
from agents.validation_agent import ValidationResult


class TravelState(TypedDict):
    """State shared across all nodes in the travel planning graph."""

    # Input
    city: str
    num_days: int
    budget: float
    quiz_answers: dict[str, list[str] | str]

    # Intermediate results
    profile: TravelProfile | None
    attractions: list[Attraction]
    itinerary: Itinerary | None
    validation_result: ValidationResult | None

    # Control flow
    retry_count: int
    errors: list[str]
    status: str  # "running", "completed", "failed"
