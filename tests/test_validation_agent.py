"""Tests for the Validation Agent."""

from unittest.mock import MagicMock
from agents.validation_agent import ValidationAgent, ValidationResult
from models.attraction import Attraction
from models.itinerary import Itinerary, DayPlan, RouteSegment
from models.profile import TravelProfile, TravelStyle, Pace, BudgetLevel


def _make_attraction(
    name: str = "Test Museum",
    place_id: str = "place_123",
    price_level: int | None = 2,
) -> Attraction:
    """Create a test attraction."""
    return Attraction(
        place_id=place_id,
        name=name,
        address="Test Address",
        lat=50.06,
        lng=19.94,
        rating=4.5,
        price_level=price_level,
        visit_duration_minutes=60,
        opening_hours={"Monday": "9:00–17:00"},
    )


def _make_itinerary(attractions: list[Attraction] | None = None) -> Itinerary:
    """Create a test itinerary."""
    if attractions is None:
        attractions = [_make_attraction()]

    day = DayPlan(
        day_number=1,
        attractions=attractions,
        route_segments=[],
        total_travel_minutes=30,
        total_visit_minutes=60,
        start_time="09:00",
        end_time="10:30",
    )
    return Itinerary(
        city="Kraków",
        num_days=1,
        days=[day],
        total_attractions=len(attractions),
    )


def _make_profile(budget: str = "medium") -> TravelProfile:
    """Create a test travel profile."""
    return TravelProfile(
        style=TravelStyle.CULTURAL,
        pace=Pace.MODERATE,
        budget=BudgetLevel(budget),
        preferred_categories=["museum"],
        interests=["history"],
        summary="Test profile",
    )


class TestValidationAgent:
    """Test suite for ValidationAgent."""

    def _make_agent(self, place_exists: bool = True) -> tuple[ValidationAgent, MagicMock]:
        """Create a ValidationAgent with mocked Maps service."""
        mock_maps = MagicMock()
        if place_exists:
            mock_maps.get_place_details.return_value = {"name": "Test"}
        else:
            mock_maps.get_place_details.return_value = {}
        return ValidationAgent(mock_maps), mock_maps

    def test_valid_itinerary_is_approved(self):
        agent, _ = self._make_agent()
        itinerary = _make_itinerary()

        result = agent.validate(itinerary, _make_profile())

        assert result.approved is True
        assert len(result.errors) == 0

    def test_missing_place_id_is_error(self):
        agent, _ = self._make_agent()
        attr = _make_attraction(place_id="")
        itinerary = _make_itinerary([attr])

        result = agent.validate(itinerary, _make_profile())

        assert result.approved is False
        assert any("place_id" in e for e in result.errors)

    def test_nonexistent_place_is_error(self):
        agent, _ = self._make_agent(place_exists=False)
        itinerary = _make_itinerary()

        result = agent.validate(itinerary, _make_profile())

        assert result.approved is False
        assert any("nie została znaleziona" in e for e in result.errors)

    def test_duplicate_attractions_is_error(self):
        agent, _ = self._make_agent()
        attr = _make_attraction()
        # Same attraction twice
        itinerary = _make_itinerary([attr, attr])

        result = agent.validate(itinerary, _make_profile())

        assert result.approved is False
        assert any("więcej niż raz" in e for e in result.errors)

    def test_expensive_attraction_on_low_budget_is_warning(self):
        agent, _ = self._make_agent()
        attr = _make_attraction(price_level=4)  # Very expensive
        itinerary = _make_itinerary([attr])

        result = agent.validate(itinerary, _make_profile(budget="low"))

        assert len(result.warnings) > 0
        assert any("budżet" in w.lower() for w in result.warnings)

    def test_all_closed_attraction_is_error(self):
        agent, _ = self._make_agent()
        attr = _make_attraction()
        attr = attr.model_copy(update={
            "opening_hours": {
                "Monday": "Closed",
                "Tuesday": "Closed",
                "Wednesday": "Closed",
                "Thursday": "Closed",
                "Friday": "Closed",
                "Saturday": "Closed",
                "Sunday": "Closed",
            }
        })
        itinerary = _make_itinerary([attr])

        result = agent.validate(itinerary, _make_profile())

        assert result.approved is False
        assert any("zamknięte" in e for e in result.errors)

    def test_empty_itinerary_passes(self):
        agent, _ = self._make_agent()
        itinerary = Itinerary(
            city="Test",
            num_days=1,
            days=[DayPlan(
                day_number=1,
                attractions=[],
                route_segments=[],
                start_time="09:00",
                end_time="09:00",
            )],
            total_attractions=0,
        )

        result = agent.validate(itinerary, _make_profile())

        # Empty is technically valid (no bad data)
        assert isinstance(result, ValidationResult)


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_default_values(self):
        result = ValidationResult()
        assert result.approved is False
        assert result.errors == []
        assert result.warnings == []

    def test_approved_state(self):
        result = ValidationResult(approved=True)
        assert result.approved is True

    def test_with_errors(self):
        result = ValidationResult(errors=["error 1", "error 2"])
        assert len(result.errors) == 2
