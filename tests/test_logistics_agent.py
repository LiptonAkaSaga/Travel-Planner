"""Tests for the Logistics Agent."""

from unittest.mock import MagicMock
from agents.logistics_agent import LogisticsAgent, _haversine
from models.attraction import Attraction
from models.profile import TravelProfile, TravelStyle, Pace, BudgetLevel
from models.itinerary import RouteSegment


def _make_attraction(name: str, lat: float, lng: float) -> Attraction:
    """Create a test attraction at a specific location."""
    return Attraction(
        place_id=f"place_{name.lower().replace(' ', '_')}",
        name=name,
        address="Test Address",
        lat=lat,
        lng=lng,
        rating=4.0,
        visit_duration_minutes=60,
    )


def _make_profile(pace: str = "moderate") -> TravelProfile:
    """Create a test travel profile."""
    return TravelProfile(
        style=TravelStyle.CULTURAL,
        pace=Pace(pace),
        budget=BudgetLevel.MEDIUM,
        preferred_categories=["museum"],
        interests=["history"],
        summary="Test profile",
    )


def _make_attractions_group() -> list[Attraction]:
    """Create a group of test attractions in Kraków."""
    return [
        _make_attraction("Wawel", 50.054, 19.935),
        _make_attraction("Rynek", 50.061, 19.937),
        _make_attraction("Kazimierz", 50.048, 19.945),
        _make_attraction("Planty", 50.058, 19.940),
        _make_attraction("Muzeum Narodowe", 50.060, 19.925),
    ]


class TestLogisticsAgent:
    """Test suite for LogisticsAgent."""

    def _make_agent(self) -> tuple[LogisticsAgent, MagicMock]:
        """Create a LogisticsAgent with mocked Maps service."""
        mock_maps = MagicMock()
        mock_maps.get_route.return_value = None  # Use fallback calculation
        return LogisticsAgent(mock_maps), mock_maps

    def test_plan_itinerary_returns_itinerary(self):
        agent, _ = self._make_agent()
        attractions = _make_attractions_group()

        result = agent.plan_itinerary("Kraków", attractions, 2, _make_profile())

        assert result.city == "Kraków"
        assert result.num_days == 2
        assert len(result.days) == 2
        assert result.total_attractions > 0

    def test_plan_itinerary_distributes_across_days(self):
        agent, _ = self._make_agent()
        attractions = _make_attractions_group()

        result = agent.plan_itinerary("Kraków", attractions, 2, _make_profile())

        # Each day should have at least 1 attraction
        for day in result.days:
            assert len(day.attractions) >= 1

    def test_plan_itinerary_optimizes_route(self):
        agent, _ = self._make_agent()
        # Attractions far apart
        attractions = [
            _make_attraction("A", 50.06, 19.94),
            _make_attraction("B", 50.05, 19.93),
            _make_attraction("C", 50.07, 19.95),
        ]

        result = agent.plan_itinerary("Test", attractions, 1, _make_profile())

        # Should have route segments
        assert len(result.days[0].route_segments) == 2

    def test_plan_itinerary_calculates_times(self):
        agent, _ = self._make_agent()
        attractions = _make_attractions_group()

        result = agent.plan_itinerary("Kraków", attractions, 1, _make_profile())

        day = result.days[0]
        assert day.total_visit_minutes > 0
        assert day.start_time == "09:00"
        assert day.end_time != ""

    def test_plan_itinerary_empty_attractions(self):
        agent, _ = self._make_agent()

        result = agent.plan_itinerary("Kraków", [], 1, _make_profile())

        assert result.total_attractions == 0
        assert len(result.days) == 1

    def test_cluster_by_day_balances_groups(self):
        agent, _ = self._make_agent()
        attractions = _make_attractions_group()

        groups = agent._cluster_by_day(attractions, 2)

        assert len(groups) == 2
        total = sum(len(g) for g in groups)
        assert total == len(attractions)

    def test_optimize_route_short_list(self):
        agent, _ = self._make_agent()
        attractions = [_make_attraction("A", 50.06, 19.94)]

        result = agent._optimize_route(attractions)

        assert len(result) == 1

    def test_calculate_segments_uses_maps_service(self):
        agent, mock_maps = self._make_agent()
        segment = RouteSegment(
            from_name="A", to_name="B",
            from_lat=50.06, from_lng=19.94,
            to_lat=50.05, to_lng=19.93,
            distance_meters=1000, duration_minutes=12,
        )
        mock_maps.get_route.return_value = segment

        attractions = [
            _make_attraction("A", 50.06, 19.94),
            _make_attraction("B", 50.05, 19.93),
        ]

        segments = agent._calculate_segments(attractions, _make_profile())

        assert len(segments) == 1
        mock_maps.get_route.assert_called_once()


class TestHaversine:
    """Test the haversine distance function."""

    def test_same_point_is_zero(self):
        assert _haversine(50.06, 19.94, 50.06, 19.94) == 0.0

    def test_known_distance(self):
        # Kraków to Warszawa ~295 km
        dist = _haversine(50.06, 19.94, 52.23, 21.01)
        assert 250 < dist < 350

    def test_symmetric(self):
        d1 = _haversine(50.06, 19.94, 52.23, 21.01)
        d2 = _haversine(52.23, 21.01, 50.06, 19.94)
        assert abs(d1 - d2) < 0.001
