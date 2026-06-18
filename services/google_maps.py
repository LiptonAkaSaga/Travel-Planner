"""Google Maps API service for places and directions."""

import googlemaps
from models.attraction import Attraction
from models.itinerary import RouteSegment
import config


class GoogleMapsService:
    """Wrapper around Google Maps Python client."""

    def __init__(self, api_key: str = "") -> None:
        key = api_key or config.GOOGLE_MAPS_API_KEY
        if not key:
            raise ValueError("GOOGLE_MAPS_API_KEY is required")
        self._client = googlemaps.Client(key=key)

    def search_attractions(
        self,
        city: str,
        categories: list[str],
        max_results: int = 20,
    ) -> list[Attraction]:
        """Search for attractions in a city filtered by categories.

        Args:
            city: Target city name.
            categories: Category filters (e.g., ["museum", "park"]).
            max_results: Maximum number of results to return.

        Returns:
            List of Attraction objects from Google Maps.
        """
        attractions: list[Attraction] = []
        seen_place_ids: set[str] = set()

        for category in categories:
            query = f"{category} in {city}"
            try:
                results = self._client.places(query=query)
            except Exception:
                continue

            for place in results.get("results", []):
                if len(attractions) >= max_results:
                    break

                place_id = place.get("place_id", "")
                if not place_id or place_id in seen_place_ids:
                    continue
                seen_place_ids.add(place_id)

                attraction = self._parse_place(place, category)
                if attraction:
                    attractions.append(attraction)

        return attractions

    def get_place_details(self, place_id: str) -> dict:
        """Get detailed information for a place.

        Args:
            place_id: Google Maps place ID.

        Returns:
            Place details dictionary.
        """
        try:
            result = self._client.place(place_id=place_id)
            return result.get("result", {})
        except Exception:
            return {}

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
        except Exception:
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
        """Get routes between consecutive waypoints.

        Args:
            waypoints: List of (lat, lng) tuples.
            mode: Travel mode.

        Returns:
            List of RouteSegment objects.
        """
        segments: list[RouteSegment] = []
        for i in range(len(waypoints) - 1):
            segment = self.get_route(waypoints[i], waypoints[i + 1], mode)
            if segment:
                segments.append(segment)
        return segments

    def _parse_place(self, place: dict, category: str) -> Attraction | None:
        """Parse a Google Maps place result into an Attraction.

        Args:
            place: Raw place result from Google Maps.
            category: The search category used.

        Returns:
            Attraction or None if parsing fails.
        """
        try:
            location = place.get("geometry", {}).get("location", {})
            if not location:
                return None

            price_level = place.get("price_level")
            opening_hours_raw = place.get("opening_hours", {})
            opening_hours: dict[str, str] = {}
            if opening_hours_raw and "weekday_text" in opening_hours_raw:
                days = [
                    "Monday", "Tuesday", "Wednesday", "Thursday",
                    "Friday", "Saturday", "Sunday",
                ]
                for day_text in opening_hours_raw.get("weekday_text", []):
                    for day in days:
                        if day_text.startswith(day):
                            opening_hours[day] = day_text.split(": ", 1)[-1]
                            break

            return Attraction(
                place_id=place.get("place_id", ""),
                name=place.get("name", "Unknown"),
                address=place.get("formatted_address", place.get("vicinity", "")),
                lat=location.get("lat", 0.0),
                lng=location.get("lng", 0.0),
                rating=place.get("rating", 0.0),
                user_ratings_total=place.get("user_ratings_total", 0),
                categories=[category],
                price_level=price_level,
                opening_hours=opening_hours,
                visit_duration_minutes=config.CATEGORY_DURATIONS.get(
                    category, config.DEFAULT_VISIT_DURATION
                ),
            )
        except (KeyError, TypeError):
            return None
