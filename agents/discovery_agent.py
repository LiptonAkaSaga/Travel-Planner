"""Discovery Agent — retrieves attractions from Google Maps based on travel profile."""

from models.profile import TravelProfile
from models.attraction import Attraction
from services.google_maps import GoogleMapsService
from services.gemini import GeminiService
import config


class DiscoveryAgent:
    """Agent responsible for discovering attractions matching the travel profile."""

    def __init__(
        self,
        maps_service: GoogleMapsService,
        gemini_service: GeminiService,
    ) -> None:
        self._maps = maps_service
        self._gemini = gemini_service

    def discover(
        self,
        city: str,
        profile: TravelProfile,
        num_days: int,
    ) -> list[Attraction]:
        """Discover attractions in a city matching the travel profile.

        Args:
            city: Target city name.
            profile: User's travel profile.
            num_days: Number of trip days.

        Returns:
            List of Attraction objects sorted by relevance.
        """
        # Calculate how many attractions we need
        pace_multiplier = {
            "relaxed": config.MIN_ATTRACTIONS_PER_DAY,
            "moderate": (config.MIN_ATTRACTIONS_PER_DAY + config.MAX_ATTRACTIONS_PER_DAY) // 2,
            "intense": config.MAX_ATTRACTIONS_PER_DAY,
        }
        target_count = pace_multiplier.get(profile.pace.value, 4) * num_days

        # Search Google Maps for each preferred category
        raw_attractions = self._maps.search_attractions(
            city=city,
            categories=profile.preferred_categories,
            max_results=target_count * 2,  # Fetch extra for filtering
        )

        # Filter out avoided categories
        filtered = [
            a for a in raw_attractions
            if not any(cat in profile.avoid_categories for cat in a.categories)
        ]

        # Score and sort by relevance to profile
        scored = self._score_attractions(filtered, profile)

        # Return top N
        return scored[:target_count]

    def enrich_attraction(self, attraction: Attraction) -> Attraction:
        """Enrich an attraction with additional details from Google Maps.

        Args:
            attraction: Attraction to enrich.

        Returns:
            Enriched Attraction with description and more details.
        """
        details = self._maps.get_place_details(attraction.place_id)
        if not details:
            return attraction

        # Update opening hours if available
        if "opening_hours" in details and "weekday_text" in details["opening_hours"]:
            days = [
                "Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday",
            ]
            opening_hours: dict[str, str] = {}
            for day_text in details["opening_hours"]["weekday_text"]:
                for day in days:
                    if day_text.startswith(day):
                        opening_hours[day] = day_text.split(": ", 1)[-1]
                        break
            attraction = attraction.model_copy(update={"opening_hours": opening_hours})

        # Generate description using Gemini
        if not attraction.description:
            description = self._generate_description(attraction)
            attraction = attraction.model_copy(update={"description": description})

        return attraction

    def _score_attractions(
        self,
        attractions: list[Attraction],
        profile: TravelProfile,
    ) -> list[Attraction]:
        """Score and sort attractions by relevance to the travel profile.

        Args:
            attractions: List of attractions to score.
            profile: User's travel profile.

        Returns:
            Sorted list of attractions (most relevant first).
        """
        def score(a: Attraction) -> float:
            s = 0.0

            # Rating weight (0-5 → 0-50)
            s += a.rating * 10

            # Category match weight
            matching_cats = sum(
                1 for cat in a.categories if cat in profile.preferred_categories
            )
            s += matching_cats * 15

            # Budget alignment
            if a.price_level is not None:
                budget_map = {"low": [0, 1], "medium": [1, 2, 3], "high": [2, 3, 4]}
                if a.price_level in budget_map.get(profile.budget.value, [1, 2, 3]):
                    s += 10

            # Popularity bonus
            if a.user_ratings_total > 100:
                s += 5
            if a.user_ratings_total > 1000:
                s += 5

            return s

        return sorted(attractions, key=score, reverse=True)

    def _generate_description(self, attraction: Attraction) -> str:
        """Generate a brief description of the attraction using Gemini.

        Args:
            attraction: Attraction to describe.

        Returns:
            Brief description string.
        """
        prompt = "Jesteś ekspertem od podróży. Napisz krótki opis (2-3 zdania) atrakcji turystycznej w języku polskim."
        message = f"Atrakcja: {attraction.name}\nAdres: {attraction.address}\nOcena: {attraction.rating}/5\nKategorie: {', '.join(attraction.categories)}"

        try:
            return self._gemini.chat(prompt, message)
        except Exception:
            return f"{attraction.name} — popularna atrakcja turystyczna."
