"""Google Maps API service — Places API (New) + Directions API."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import googlemaps
from models.attraction import Attraction
from models.itinerary import RouteSegment
import config

logger = logging.getLogger(__name__)

PLACES_BASE = "https://places.googleapis.com/v1"


class GoogleMapsService:
    """Wrapper around Google Maps APIs.

    Uses Places API (New) for search/details and Directions API for routes.
    """

    def __init__(self, api_key: str = "") -> None:
        key = api_key or config.GOOGLE_MAPS_API_KEY
        if not key:
            raise ValueError("GOOGLE_MAPS_API_KEY is required")
        self._api_key = key
        self._client = googlemaps.Client(key=key)

    # ── Places API (New) ─────────────────────────────────────────────

    def search_attractions(
        self,
        city: str,
        categories: list[str],
        max_results: int = 20,
        country: str = "",
    ) -> list[Attraction]:
        """Search for attractions using Places API (New) searchText.

        Args:
            city: Target city name.
            categories: Category filters (e.g., ["museum", "park"]).
            max_results: Maximum number of results to return.
            country: Optional country name to disambiguate the search.

        Returns:
            List of Attraction objects from Google Maps.
        """
        # Build location string with country for disambiguation
        location = f"{city}, {country}" if country else city

        # Parallel category search
        category_results: dict[str, list[dict]] = {}

        def _search_category(category: str) -> tuple[str, list[dict]]:
            query = f"{category} in {location}"
            try:
                results = self._text_search(query, max_results=max_results)
                return category, results
            except Exception as e:
                logger.warning(f"Places search failed for '{query}': {e}")
                return category, []

        with ThreadPoolExecutor(max_workers=min(len(categories), 5)) as executor:
            futures = {executor.submit(_search_category, cat): cat for cat in categories}
            for future in as_completed(futures):
                category, results = future.result()
                category_results[category] = results

        # Parse and deduplicate
        attractions: list[Attraction] = []
        seen_place_ids: set[str] = set()

        for category in categories:
            for place in category_results.get(category, []):
                if len(attractions) >= max_results:
                    break

                place_id = place.get("id", "")
                if not place_id or place_id in seen_place_ids:
                    continue
                seen_place_ids.add(place_id)

                attraction = self._parse_place_new(place, category)
                if attraction:
                    attractions.append(attraction)

        logger.info(f"Found {len(attractions)} attractions total (parallel search)")
        return attractions

    def get_place_details(self, place_id: str) -> dict:
        """Get detailed information using Places API (New).

        Args:
            place_id: Google Maps place ID.

        Returns:
            Place details dictionary.
        """
        url = f"{PLACES_BASE}/places/{place_id}"
        headers = {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": (
                "id,displayName,formattedAddress,rating,userRatingCount,"
                "priceLevel,currentOpeningHours,regularOpeningHours,"
                "location,types,editorialSummary"
            ),
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"Place details failed for {place_id}: {e}")
            return {}

    # ── Directions API (legacy — still works) ────────────────────────

    def get_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        mode: str = "walking",
    ) -> RouteSegment | None:
        """Get route between two points.

        Args:
            origin: (lat, lng) tuple for origin.
            destination: (lat, lng) tuple for destination.
            mode: Travel mode (walking, driving, transit).

        Returns:
            RouteSegment or None if route not found.
        """
        try:
            directions = self._client.directions(
                origin=origin,
                destination=destination,
                mode=mode,
            )
        except Exception as e:
            logger.warning(f"Directions API failed: {e}")
            return None

        if not directions:
            return None

        leg = directions[0]["legs"][0]
        return RouteSegment(
            from_name=f"{origin[0]},{origin[1]}",
            to_name=f"{destination[0]},{destination[1]}",
            from_lat=origin[0],
            from_lng=origin[1],
            to_lat=destination[0],
            to_lng=destination[1],
            distance_meters=leg["distance"]["value"],
            duration_minutes=leg["duration"]["value"] // 60,
            travel_mode=mode,
        )

    def get_routes_batch(
        self,
        waypoints: list[tuple[float, float]],
        mode: str = "walking",
    ) -> list[RouteSegment]:
        """Get routes between consecutive waypoints."""
        segments: list[RouteSegment] = []
        for i in range(len(waypoints) - 1):
            segment = self.get_route(waypoints[i], waypoints[i + 1], mode)
            if segment:
                segments.append(segment)
        return segments

    # ── Private helpers ──────────────────────────────────────────────

    def _text_search(self, query: str, max_results: int = 20) -> list[dict]:
        """Call Places API (New) searchText endpoint.

        Args:
            query: Search query string.
            max_results: Max results to return.

        Returns:
            List of place dictionaries.
        """
        url = f"{PLACES_BASE}/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.rating,places.userRatingCount,places.priceLevel,"
                "places.location,places.types,places.currentOpeningHours,"
                "places.regularOpeningHours"
            ),
        }
        body = {
            "textQuery": query,
            "maxResultCount": min(max_results, 20),
            "languageCode": "pl",
        }

        resp = requests.post(url, headers=headers, json=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("places", [])

    def _parse_place_new(self, place: dict, category: str) -> Attraction | None:
        """Parse a Places API (New) result into an Attraction.

        Args:
            place: Raw place result from Places API (New).
            category: The search category used.

        Returns:
            Attraction or None if parsing fails.
        """
        try:
            location = place.get("location", {})
            lat = location.get("latitude", 0.0)
            lng = location.get("longitude", 0.0)
            if not lat and not lng:
                return None

            # Display name
            display_name = place.get("displayName", {})
            name = display_name.get("text", "Unknown") if isinstance(display_name, dict) else str(display_name)

            # Opening hours
            opening_hours: dict[str, str] = {}
            regular_hours = place.get("regularOpeningHours", {})
            if regular_hours and "weekdayDescriptions" in regular_hours:
                days = [
                    "Monday", "Tuesday", "Wednesday", "Thursday",
                    "Friday", "Saturday", "Sunday",
                ]
                for desc in regular_hours["weekdayDescriptions"]:
                    for day in days:
                        if desc.startswith(day):
                            opening_hours[day] = desc.split(": ", 1)[-1]
                            break

            # Price level mapping (new API uses string enum)
            price_level_raw = place.get("priceLevel")
            price_level_map = {
                "PRICE_LEVEL_FREE": 0,
                "PRICE_LEVEL_INEXPENSIVE": 1,
                "PRICE_LEVEL_MODERATE": 2,
                "PRICE_LEVEL_EXPENSIVE": 3,
                "PRICE_LEVEL_VERY_EXPENSIVE": 4,
            }
            price_level = price_level_map.get(price_level_raw) if price_level_raw else None

            return Attraction(
                place_id=place.get("id", ""),
                name=name,
                address=place.get("formattedAddress", ""),
                lat=lat,
                lng=lng,
                rating=place.get("rating", 0.0),
                user_ratings_total=place.get("userRatingCount", 0),
                categories=[category],
                price_level=price_level,
                opening_hours=opening_hours,
                visit_duration_minutes=config.CATEGORY_DURATIONS.get(
                    category, config.DEFAULT_VISIT_DURATION
                ),
            )
        except (KeyError, TypeError) as e:
            logger.warning(f"Failed to parse place: {e}")
            return None
