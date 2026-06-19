"""Logistics Agent — route optimization and schedule generation."""

import logging
from math import radians, sin, cos, sqrt, atan2
from models.attraction import Attraction
from models.itinerary import Itinerary, DayPlan, RouteSegment
from models.meal import MealType, MealSlot, MEAL_WINDOWS, MEAL_DURATIONS, MEAL_LABELS, MEAL_ICONS
from models.profile import TravelProfile
from services.google_maps import GoogleMapsService
import config

logger = logging.getLogger(__name__)


class LogisticsAgent:
    """Agent responsible for route optimization and schedule generation."""

    def __init__(self, maps_service: GoogleMapsService) -> None:
        self._maps = maps_service

    def plan_itinerary(
        self,
        city: str,
        attractions: list[Attraction],
        num_days: int,
        profile: TravelProfile,
        restaurants: dict[MealType, list[Attraction]] | None = None,
    ) -> Itinerary:
        """Create an optimized multi-day itinerary.

        Args:
            city: Target city name.
            attractions: List of attractions to schedule.
            num_days: Number of days.
            profile: User's travel profile.
            restaurants: Optional dict of restaurants by meal type.

        Returns:
            Optimized Itinerary with daily plans.
        """
        # Cluster attractions into daily groups by geography
        daily_groups = self._cluster_by_day(attractions, num_days)

        # Optimize each day's route
        days: list[DayPlan] = []
        total_travel = 0

        for day_num, group in enumerate(daily_groups, start=1):
            # Optimize ordering using nearest neighbor
            ordered = self._optimize_route(group)

            # Calculate route segments
            segments = self._calculate_segments(ordered, profile)

            # Calculate times
            visit_minutes = sum(a.visit_duration_minutes for a in ordered)
            travel_minutes = sum(s.duration_minutes for s in segments)
            total_minutes = visit_minutes + travel_minutes

            start_hour = config.START_HOUR
            end_minutes = start_hour * 60 + total_minutes
            end_hour = int(end_minutes // 60)
            end_min = int(end_minutes % 60)

            day = DayPlan(
                day_number=day_num,
                attractions=ordered,
                route_segments=segments,
                total_travel_minutes=travel_minutes,
                total_visit_minutes=visit_minutes,
                start_time=f"{start_hour:02d}:00",
                end_time=f"{end_hour:02d}:{end_min:02d}",
            )

            # Insert meals if restaurants are provided
            if restaurants and profile.meal_preferences:
                day = self._insert_meals(day, restaurants, profile, day_num)

            days.append(day)
            total_travel += travel_minutes

        total_attractions = sum(len(d.attractions) for d in days)

        return Itinerary(
            city=city,
            num_days=num_days,
            days=days,
            total_attractions=total_attractions,
            total_travel_minutes=total_travel,
            summary=f"{total_attractions} atrakcji w {num_days} dni w mieście {city}",
        )

    def _cluster_by_day(
        self,
        attractions: list[Attraction],
        num_days: int,
    ) -> list[list[Attraction]]:
        """Cluster attractions into daily groups using geographic proximity.

        Uses a simple greedy approach: assign each attraction to the day
        whose centroid is closest.

        Args:
            attractions: List of attractions.
            num_days: Number of days.

        Returns:
            List of lists, one per day.
        """
        if not attractions:
            return [[] for _ in range(num_days)]

        # Initialize day groups with k-means-like seeding
        groups: list[list[Attraction]] = [[] for _ in range(num_days)]

        # Spread first N attractions as initial centroids
        step = max(1, len(attractions) // num_days)
        centroids: list[tuple[float, float]] = []
        for i in range(num_days):
            idx = min(i * step, len(attractions) - 1)
            centroids.append((attractions[idx].lat, attractions[idx].lng))

        # Assign each attraction to nearest centroid
        for attr in attractions:
            best_day = 0
            best_dist = float("inf")
            for day_idx, (clat, clng) in enumerate(centroids):
                dist = _haversine(attr.lat, attr.lng, clat, clng)
                if dist < best_dist:
                    best_dist = dist
                    best_day = day_idx
            groups[best_day].append(attr)

        # Update centroids after assignment
        for day_idx, group in enumerate(groups):
            if group:
                avg_lat = sum(a.lat for a in group) / len(group)
                avg_lng = sum(a.lng for a in group) / len(group)
                centroids[day_idx] = (avg_lat, avg_lng)

        # Reassign for balance
        groups = self._balance_groups(groups, centroids)

        return groups

    def _balance_groups(
        self,
        groups: list[list[Attraction]],
        centroids: list[tuple[float, float]],
    ) -> list[list[Attraction]]:
        """Balance attraction counts across days.

        Moves attractions from overfull days to underfull days
        based on proximity to the target day's centroid.

        Args:
            groups: Current day groupings.
            centroids: Centroid for each day.

        Returns:
            Balanced day groupings.
        """
        total = sum(len(g) for g in groups)
        num_days = len(groups)
        if num_days == 0:
            return groups

        target_per_day = total // num_days
        remainder = total % num_days

        # Sort groups by size (largest first)
        indexed = sorted(enumerate(groups), key=lambda x: len(x[1]), reverse=True)

        balanced: list[list[Attraction]] = [[] for _ in range(num_days)]

        # Redistribute
        all_attractions: list[Attraction] = []
        for group in groups:
            all_attractions.extend(group)

        # Sort by lat/lng for geographic coherence
        all_attractions.sort(key=lambda a: (a.lat, a.lng))

        idx = 0
        for day in range(num_days):
            limit = target_per_day + (1 if day < remainder else 0)
            for _ in range(limit):
                if idx < len(all_attractions):
                    balanced[day].append(all_attractions[idx])
                    idx += 1

        return balanced

    def _optimize_route(self, attractions: list[Attraction]) -> list[Attraction]:
        """Optimize attraction order using nearest neighbor heuristic.

        Args:
            attractions: List of attractions for one day.

        Returns:
            Reordered list with optimized visiting order.
        """
        if len(attractions) <= 2:
            return attractions

        # Start with the attraction that has the earliest opening
        ordered: list[Attraction] = [attractions[0]]
        remaining = list(attractions[1:])

        while remaining:
            current = ordered[-1]
            nearest_idx = 0
            nearest_dist = float("inf")

            for i, candidate in enumerate(remaining):
                dist = _haversine(
                    current.lat, current.lng,
                    candidate.lat, candidate.lng,
                )
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i

            ordered.append(remaining.pop(nearest_idx))

        return ordered

    def _calculate_segments(
        self,
        attractions: list[Attraction],
        profile: TravelProfile,
    ) -> list[RouteSegment]:
        """Calculate route segments between consecutive attractions.

        Args:
            attractions: Ordered list of attractions.
            profile: User's travel profile.

        Returns:
            List of RouteSegment objects.
        """
        if len(attractions) < 2:
            return []

        # Determine travel mode based on distances
        segments: list[RouteSegment] = []
        for i in range(len(attractions) - 1):
            origin = (attractions[i].lat, attractions[i].lng)
            dest = (attractions[i + 1].lat, attractions[i + 1].lng)

            dist = _haversine(origin[0], origin[1], dest[0], dest[1])

            # Choose travel mode based on distance
            if dist < 1.0:  # < 1km
                mode = "walking"
            elif dist < 3.0:  # 1-3km
                mode = "walking" if profile.pace.value != "relaxed" else "transit"
            else:
                mode = "transit"

            # Try Google Directions API first
            segment = self._maps.get_route(origin, dest, mode)

            if segment:
                segments.append(segment)
            else:
                # Fallback: estimate from distance
                speed = {
                    "walking": config.WALKING_SPEED_KMH,
                    "transit": config.TRANSIT_SPEED_KMH,
                    "driving": config.DRIVING_SPEED_KMH,
                }.get(mode, config.WALKING_SPEED_KMH)

                duration = int((dist / speed) * 60)  # minutes

                segments.append(RouteSegment(
                    from_name=attractions[i].name,
                    to_name=attractions[i + 1].name,
                    from_lat=origin[0],
                    from_lng=origin[1],
                    to_lat=dest[0],
                    to_lng=dest[1],
                    distance_meters=int(dist * 1000),
                    duration_minutes=duration,
                    travel_mode=mode,
                ))

        return segments

    def _insert_meals(
        self,
        day: DayPlan,
        restaurants: dict[MealType, list[Attraction]],
        profile: TravelProfile,
        day_number: int,
    ) -> DayPlan:
        """Insert meal slots into a day plan.

        Picks the nearest restaurant to the current location at each meal time.

        Args:
            day: The day plan to insert meals into.
            restaurants: Available restaurants by meal type.
            profile: User's travel profile with meal preferences.
            day_number: Current day number (1-based) for restaurant rotation.

        Returns:
            Updated DayPlan with meals inserted.
        """
        meal_preferences = profile.meal_preferences
        if not meal_preferences:
            return day

        meals: list[MealSlot] = []
        current_minutes = _time_to_minutes(day.start_time)

        # Sort meal types by their time window
        ordered_meals = sorted(
            [MealType(mt) for mt, count in meal_preferences.items() if count > 0],
            key=lambda mt: MEAL_WINDOWS[mt][0],
        )

        # Find current location at each meal time
        attractions = list(day.attractions)

        for meal_type in ordered_meals:
            window_start, window_end = MEAL_WINDOWS[meal_type]
            duration = MEAL_DURATIONS[meal_type]

            # Determine where we are at meal time
            meal_minutes = max(window_start * 60, current_minutes)
            if meal_minutes > window_end * 60:
                # Too late for this meal, skip
                logger.warning(f"Skipping {meal_type.value} - too late in schedule")
                continue

            # Find nearest restaurant to current location
            available = restaurants.get(meal_type, [])
            if not available:
                continue

            # Pick restaurant (rotate by day number for variety)
            idx = (day_number - 1) % len(available)
            restaurant = available[idx]

            # Create meal slot
            meal_hour = meal_minutes // 60
            meal_min = meal_minutes % 60
            meals.append(MealSlot(
                meal_type=meal_type,
                restaurant_name=restaurant.name,
                restaurant_address=restaurant.address,
                place_id=restaurant.place_id,
                rating=restaurant.rating,
                price_level=restaurant.price_level,
                duration_minutes=duration,
                scheduled_time=f"{meal_hour:02d}:{meal_min:02d}",
                lat=restaurant.lat,
                lng=restaurant.lng,
                description=restaurant.description,
            ))

            # Advance time by meal duration
            current_minutes = meal_minutes + duration

        if not meals:
            return day

        # Recalculate end time including meals
        total_meal_minutes = sum(m.duration_minutes for m in meals)
        total_minutes = day.total_visit_minutes + day.total_travel_minutes + total_meal_minutes
        start_minutes = _time_to_minutes(day.start_time)
        end_minutes = start_minutes + total_minutes
        end_hour = int(end_minutes // 60)
        end_min = int(end_minutes % 60)

        return day.model_copy(update={
            "meals": meals,
            "end_time": f"{end_hour:02d}:{end_min:02d}",
        })


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in km using Haversine formula."""
    R = 6371.0  # Earth radius in km

    lat1_r, lng1_r = radians(lat1), radians(lng1)
    lat2_r, lng2_r = radians(lat2), radians(lng2)

    dlat = lat2_r - lat1_r
    dlng = lng2_r - lng1_r

    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c
