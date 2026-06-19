"""Discovery Agent — retrieves attractions from Google Maps based on travel profile."""

import json
import logging
from models.profile import TravelProfile
from models.attraction import Attraction
from models.meal import MealType, MealSlot, MEAL_DURATIONS
from services.google_maps import GoogleMapsService
from services.llm import LLMService
import config

logger = logging.getLogger(__name__)


class DiscoveryAgent:
    """Agent responsible for discovering attractions matching the travel profile."""

    def __init__(
        self,
        maps_service: GoogleMapsService,
        llm_service: LLMService,
    ) -> None:
        self._maps = maps_service
        self._llm = llm_service

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

    def enrich_attraction(
        self,
        attraction: Attraction,
        place_details_cache: dict[str, dict] | None = None,
    ) -> Attraction:
        """Enrich an attraction with additional details from Google Maps.

        Args:
            attraction: Attraction to enrich.
            place_details_cache: Optional cache for place details.

        Returns:
            Enriched Attraction with opening hours (description deferred to batch).
        """
        cache = place_details_cache if place_details_cache is not None else {}

        # Check cache first
        if attraction.place_id in cache:
            details = cache[attraction.place_id]
        else:
            details = self._maps.get_place_details(attraction.place_id)
            if details:
                cache[attraction.place_id] = details

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

        return attraction

    def batch_generate_descriptions(self, attractions: list[Attraction]) -> list[Attraction]:
        """Generate descriptions for multiple attractions in a single LLM call.

        Args:
            attractions: List of attractions to generate descriptions for.

        Returns:
            Attractions with descriptions filled in.
        """
        needs_desc = [a for a in attractions if not a.description]
        if not needs_desc:
            return attractions

        # Build batch prompt
        attraction_lines = []
        for i, a in enumerate(needs_desc, 1):
            attraction_lines.append(
                f"{i}. {a.name} — {a.address} (ocena: {a.rating}/5, kategorie: {', '.join(a.categories)})"
            )

        system_prompt = (
            "Jesteś ekspertem od podróży. Dla każdej z poniższych atrakcji napisz krótki opis (2-3 zdania) w języku polskim.\n"
            "Zwróć TYLKO tablicę JSON: [{\"name\": \"...\", \"description\": \"...\"}, ...]\n"
            "Każdy opis powinien być atrakcyjny i informacyjny."
        )
        user_message = "Atrakcje:\n" + "\n".join(attraction_lines)

        try:
            result = self._llm.chat(system_prompt, user_message)
            # Parse JSON from response
            json_str = result.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            descriptions = json.loads(json_str)

            # Map descriptions by name
            desc_map = {d["name"]: d["description"] for d in descriptions if "name" in d and "description" in d}

            # Apply descriptions
            result_list = []
            for a in attractions:
                if not a.description and a.name in desc_map:
                    result_list.append(a.model_copy(update={"description": desc_map[a.name]}))
                else:
                    result_list.append(a)

            logger.info(f"Batch generated descriptions for {len(desc_map)}/{len(needs_desc)} attractions")
            return result_list

        except Exception as e:
            logger.warning(f"Batch description generation failed: {e}")
            # Fallback: generate individually (but still return all)
            result_list = []
            for a in attractions:
                if not a.description:
                    result_list.append(a.model_copy(update={"description": self._generate_description(a)}))
                else:
                    result_list.append(a)
            return result_list

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

    def discover_restaurants(
        self,
        city: str,
        profile: TravelProfile,
        meal_types: list[MealType],
        num_days: int,
    ) -> dict[MealType, list[Attraction]]:
        """Discover restaurants for specific meal types.

        Args:
            city: Target city name.
            profile: User's travel profile.
            meal_types: Which meal types to find restaurants for.
            num_days: Number of trip days.

        Returns:
            Dictionary mapping meal type to list of restaurant attractions.
        """
        results: dict[MealType, list[Attraction]] = {}

        # Build dietary filter for search query
        dietary_filter = ""
        if profile.dietary_restrictions:
            dietary_map = {
                "vegetarian": "wegetariańska",
                "vegan": "wegańska",
                "halal": "halal",
                "kosher": "koszerna",
                "gluten_free": "bezglutenowa",
            }
            dietary_labels = [dietary_map.get(d, d) for d in profile.dietary_restrictions]
            dietary_filter = " " + " ".join(dietary_labels)

        for meal_type in meal_types:
            # Build search query based on meal type
            query_map = {
                MealType.BREAKFAST: f"śniadanie kawiarnia{dietary_filter} in {city}",
                MealType.LUNCH: f"restauracja obiad{dietary_filter} in {city}",
                MealType.DINNER: f"restauracja kolacja{dietary_filter} in {city}",
            }
            query = query_map[meal_type]

            try:
                raw = self._maps.search_attractions(
                    city=city,
                    categories=["restaurant"],
                    max_results=num_days * 3,  # Extra for variety
                )
                # Filter and score
                scored = self._score_attractions(raw, profile)
                results[meal_type] = scored[:num_days + 2]  # Enough for each day + variety
                logger.info(f"Found {len(results[meal_type])} restaurants for {meal_type.value}")
            except Exception as e:
                logger.warning(f"Restaurant discovery failed for {meal_type.value}: {e}")
                results[meal_type] = []

        return results

    def _generate_description(self, attraction: Attraction) -> str:
        """Generate a brief description of the attraction using LLM.

        Args:
            attraction: Attraction to describe.

        Returns:
            Brief description string.
        """
        prompt = "Jesteś ekspertem od podróży. Napisz krótki opis (2-3 zdania) atrakcji turystycznej w języku polskim."
        message = f"Atrakcja: {attraction.name}\nAdres: {attraction.address}\nOcena: {attraction.rating}/5\nKategorie: {', '.join(attraction.categories)}"

        try:
            return self._llm.chat(prompt, message)
        except Exception:
            return f"{attraction.name} — popularna atrakcja turystyczna."
