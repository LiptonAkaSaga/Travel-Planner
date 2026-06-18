"""Tests for the Discovery Agent."""

from unittest.mock import MagicMock
from agents.discovery_agent import DiscoveryAgent
from models.profile import TravelProfile, TravelStyle, Pace, BudgetLevel
from models.attraction import Attraction


def _make_profile() -> TravelProfile:
    """Create a test travel profile."""
    return TravelProfile(
        style=TravelStyle.CULTURAL,
        pace=Pace.MODERATE,
        budget=BudgetLevel.MEDIUM,
        preferred_categories=["museum", "landmark"],
        avoid_categories=["nightlife"],
        interests=["history"],
        summary="Test profile",
    )


def _make_attraction(name: str = "Test Museum", rating: float = 4.5) -> Attraction:
    """Create a test attraction."""
    return Attraction(
        place_id=f"place_{name.lower().replace(' ', '_')}",
        name=name,
        address="Test Address",
        lat=50.06,
        lng=19.94,
        rating=rating,
        user_ratings_total=100,
        categories=["museum"],
    )


class TestDiscoveryAgent:
    """Test suite for DiscoveryAgent."""

    def _make_agent(
        self,
        attractions: list[Attraction] | None = None,
    ) -> tuple[DiscoveryAgent, MagicMock, MagicMock]:
        """Create a DiscoveryAgent with mocked services."""
        mock_maps = MagicMock()
        mock_gemini = MagicMock()

        if attractions is None:
            attractions = [_make_attraction()]

        mock_maps.search_attractions.return_value = attractions
        mock_gemini.chat.return_value = "Test description"

        return DiscoveryAgent(mock_maps, mock_gemini), mock_maps, mock_gemini

    def test_discover_returns_attractions(self):
        attrs = [_make_attraction("Museum A"), _make_attraction("Museum B", 4.0)]
        agent, mock_maps, _ = self._make_agent(attrs)

        result = agent.discover("Kraków", _make_profile(), 2)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(a, Attraction) for a in result)

    def test_discover_calls_maps_service(self):
        agent, mock_maps, _ = self._make_agent()
        profile = _make_profile()

        agent.discover("Warszawa", profile, 3)

        mock_maps.search_attractions.assert_called_once()
        call_kwargs = mock_maps.search_attractions.call_args
        assert call_kwargs.kwargs["city"] == "Warszawa"

    def test_discover_filters_avoided_categories(self):
        nightlife = Attraction(
            place_id="night_1",
            name="Club X",
            lat=50.06,
            lng=19.94,
            rating=4.8,
            categories=["nightlife"],
        )
        museum = _make_attraction("Museum A")
        agent, _, _ = self._make_agent([nightlife, museum])

        result = agent.discover("Kraków", _make_profile(), 1)

        # nightlife should be filtered out
        names = [a.name for a in result]
        assert "Club X" not in names

    def test_discover_limits_by_day_count(self):
        attrs = [_make_attraction(f"A{i}", 4.0 + (i * 0.1)) for i in range(20)]
        agent, _, _ = self._make_agent(attrs)

        result = agent.discover("Kraków", _make_profile(), 2)

        # moderate pace = ~4 per day * 2 days = 8
        assert len(result) <= 8

    def test_discover_sorted_by_relevance(self):
        low_rating = _make_attraction("Low Rated", 2.0)
        high_rating = _make_attraction("High Rated", 4.9)
        agent, _, _ = self._make_agent([low_rating, high_rating])

        result = agent.discover("Kraków", _make_profile(), 1)

        # Higher rated should come first
        assert result[0].name == "High Rated"

    def test_enrich_attraction_adds_description(self):
        attraction = _make_attraction()
        agent, mock_maps, mock_gemini = self._make_agent()

        mock_maps.get_place_details.return_value = {
            "opening_hours": {"weekday_text": ["Monday: 9:00 AM – 5:00 PM"]},
        }

        enriched = agent.enrich_attraction(attraction)

        assert enriched.description != ""
        mock_gemini.chat.assert_called_once()

    def test_enrich_attraction_handles_empty_details(self):
        attraction = _make_attraction()
        agent, mock_maps, _ = self._make_agent()
        mock_maps.get_place_details.return_value = {}

        enriched = agent.enrich_attraction(attraction)

        # Should still work, just without enrichment
        assert isinstance(enriched, Attraction)
