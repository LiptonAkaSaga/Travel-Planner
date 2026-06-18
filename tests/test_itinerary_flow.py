"""Integration tests for the complete itinerary flow."""

from unittest.mock import MagicMock
from models.profile import TravelProfile, TravelStyle, Pace, BudgetLevel
from models.attraction import Attraction
from models.itinerary import Itinerary
from agents.discovery_agent import DiscoveryAgent
from agents.logistics_agent import LogisticsAgent
from agents.validation_agent import ValidationAgent


def _make_attraction(name: str, lat: float = 50.06, lng: float = 19.94) -> Attraction:
    """Create a test attraction."""
    return Attraction(
        place_id=f"place_{name.lower().replace(' ', '_')}",
        name=name,
        address=f"{name} Address",
        lat=lat,
        lng=lng,
        rating=4.5,
        user_ratings_total=200,
        categories=["museum"],
        visit_duration_minutes=60,
        opening_hours={"Monday": "9:00–17:00"},
    )


def _make_profile() -> TravelProfile:
    """Create a test travel profile."""
    return TravelProfile(
        style=TravelStyle.CULTURAL,
        pace=Pace.MODERATE,
        budget=BudgetLevel.MEDIUM,
        preferred_categories=["museum", "landmark"],
        interests=["history"],
        summary="Cultural traveler",
    )


class TestEndToEndFlow:
    """Test the complete flow: discover → plan → validate."""

    def test_full_flow_produces_valid_itinerary(self):
        # Setup mocks
        mock_maps = MagicMock()
        mock_gemini = MagicMock()

        attractions = [
            _make_attraction("Wawel", 50.054, 19.935),
            _make_attraction("Rynek Główny", 50.061, 19.937),
            _make_attraction("Kazimierz", 50.048, 19.945),
            _make_attraction("Muzeum Narodowe", 50.060, 19.925),
        ]

        mock_maps.search_attractions.return_value = attractions
        mock_maps.get_place_details.return_value = {"name": "Test"}
        mock_maps.get_route.return_value = None
        mock_gemini.chat.return_value = "Test description"

        profile = _make_profile()

        # Step 1: Discover
        discovery = DiscoveryAgent(mock_maps, mock_gemini)
        discovered = discovery.discover("Kraków", profile, 2)
        assert len(discovered) > 0

        # Step 2: Plan
        logistics = LogisticsAgent(mock_maps)
        itinerary = logistics.plan_itinerary("Kraków", discovered, 2, profile)
        assert isinstance(itinerary, Itinerary)
        assert itinerary.num_days == 2
        assert itinerary.total_attractions > 0

        # Step 3: Validate
        validation = ValidationAgent(mock_maps)
        result = validation.validate(itinerary, profile)
        assert result.approved is True

    def test_flow_with_no_attractions(self):
        mock_maps = MagicMock()
        mock_gemini = MagicMock()
        mock_maps.search_attractions.return_value = []
        mock_gemini.chat.return_value = "Description"

        profile = _make_profile()

        discovery = DiscoveryAgent(mock_maps, mock_gemini)
        discovered = discovery.discover("Kraków", profile, 1)

        assert len(discovered) == 0

        logistics = LogisticsAgent(mock_maps)
        itinerary = logistics.plan_itinerary("Kraków", discovered, 1, profile)

        assert itinerary.total_attractions == 0

    def test_validation_catches_duplicates(self):
        mock_maps = MagicMock()
        mock_maps.get_place_details.return_value = {"name": "Test"}

        attr = _make_attraction("Same Place")
        itinerary = Itinerary(
            city="Test",
            num_days=1,
            days=[],
            total_attractions=2,
        )

        from models.itinerary import DayPlan
        day = DayPlan(
            day_number=1,
            attractions=[attr, attr],
            route_segments=[],
            start_time="09:00",
            end_time="11:00",
        )
        itinerary = itinerary.model_copy(update={"days": [day]})

        validation = ValidationAgent(mock_maps)
        result = validation.validate(itinerary, _make_profile())

        assert result.approved is False
        assert any("więcej niż raz" in e for e in result.errors)
