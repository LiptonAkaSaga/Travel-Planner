"""Validation Agent — guardrails and itinerary validation."""

from dataclasses import dataclass, field
from models.attraction import Attraction
from models.itinerary import Itinerary, DayPlan
from models.profile import TravelProfile
from services.google_maps import GoogleMapsService
import config


@dataclass
class ValidationResult:
    """Result of itinerary validation."""

    approved: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ValidationAgent:
    """Agent responsible for validating itineraries before presentation."""

    def __init__(self, maps_service: GoogleMapsService) -> None:
        self._maps = maps_service

    def validate(
        self,
        itinerary: Itinerary,
        profile: TravelProfile,
        place_details_cache: dict[str, dict] | None = None,
    ) -> ValidationResult:
        """Validate an itinerary against guardrails and constraints.

        Args:
            itinerary: The itinerary to validate.
            profile: User's travel profile.
            place_details_cache: Optional cache of place details from discovery.

        Returns:
            ValidationResult with approval status and any issues.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Verify attractions exist in Google Maps
        verification_errors = self._verify_attractions_exist(itinerary, place_details_cache)
        errors.extend(verification_errors)

        # 2. Validate schedule realism
        schedule_errors, schedule_warnings = self._validate_schedule(itinerary)
        errors.extend(schedule_errors)
        warnings.extend(schedule_warnings)

        # 3. Validate budget alignment
        budget_warnings = self._validate_budget(itinerary, profile)
        warnings.extend(budget_warnings)

        # 4. Validate opening hours
        hours_errors = self._validate_opening_hours(itinerary)
        errors.extend(hours_errors)

        # 5. Check for duplicate attractions
        dup_errors = self._check_duplicates(itinerary)
        errors.extend(dup_errors)

        return ValidationResult(
            approved=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _verify_attractions_exist(
        self,
        itinerary: Itinerary,
        place_details_cache: dict[str, dict] | None = None,
    ) -> list[str]:
        """Verify every attraction exists in Google Maps by place_id.

        Uses cached data when available to avoid redundant API calls.

        Args:
            itinerary: Itinerary to verify.
            place_details_cache: Optional cache of place details.

        Returns:
            List of error messages for unverifiable attractions.
        """
        errors: list[str] = []
        cache = place_details_cache or {}

        for day in itinerary.days:
            for attraction in day.attractions:
                if not attraction.place_id:
                    errors.append(
                        f"Atrakcja '{attraction.name}' nie ma place_id z Google Maps."
                    )
                    continue

                # Use cache if available, otherwise call API
                if attraction.place_id in cache:
                    details = cache[attraction.place_id]
                else:
                    details = self._maps.get_place_details(attraction.place_id)

                if not details:
                    errors.append(
                        f"Atrakcja '{attraction.name}' (ID: {attraction.place_id}) "
                        f"nie została znaleziona w Google Maps."
                    )

        return errors

    def _validate_schedule(self, itinerary: Itinerary) -> tuple[list[str], list[str]]:
        """Validate that the schedule is realistic.

        Args:
            itinerary: Itinerary to validate.

        Returns:
            Tuple of (errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        for day in itinerary.days:
            # Check total hours
            total_minutes = day.total_visit_minutes + day.total_travel_minutes
            total_hours = total_minutes / 60

            if total_hours > config.MAX_DAILY_HOURS:
                errors.append(
                    f"Dzień {day.day_number}: plan zajmuje {total_hours:.1f}h, "
                    f"maksimum to {config.MAX_DAILY_HOURS}h."
                )

            # Check end time doesn't exceed reasonable hour
            if day.end_time:
                end_parts = day.end_time.split(":")
                if len(end_parts) == 2:
                    end_hour = int(end_parts[0])
                    if end_hour > config.END_HOUR:
                        warnings.append(
                            f"Dzień {day.day_number}: plan kończy się o {day.end_time}, "
                            f"co może być za późno."
                        )

            # Check minimum attractions
            if len(day.attractions) < 1:
                warnings.append(
                    f"Dzień {day.day_number}: brak atrakcji w planie."
                )

        return errors, warnings

    def _validate_budget(
        self,
        itinerary: Itinerary,
        profile: TravelProfile,
    ) -> list[str]:
        """Validate budget alignment between itinerary and profile.

        Supports both categorical (low/medium/high) and numeric (PLN) budgets.

        Args:
            itinerary: Itinerary to validate.
            profile: User's travel profile.

        Returns:
            List of warning messages.
        """
        warnings: list[str] = []

        # Price level cost estimates (PLN per visit)
        price_level_cost = {0: 0, 1: 30, 2: 60, 3: 120, 4: 250}

        # Numeric budget validation
        if profile.budget_amount and profile.budget_amount > 0:
            total_estimated_cost = 0.0
            for day in itinerary.days:
                for attraction in day.attractions:
                    if attraction.price_level is not None:
                        total_estimated_cost += price_level_cost.get(attraction.price_level, 0)

            if total_estimated_cost > profile.budget_amount:
                warnings.append(
                    f"Szacowany koszt atrakcji ({total_estimated_cost:.0f} PLN) "
                    f"przekracza budżet ({profile.budget_amount:.0f} PLN)."
                )

            # Per-attraction warnings for expensive items
            for day in itinerary.days:
                for attraction in day.attractions:
                    if attraction.price_level is not None and attraction.price_level >= 3:
                        cost = price_level_cost.get(attraction.price_level, 0)
                        warnings.append(
                            f"'{attraction.name}' — szacowany koszt ~{cost} PLN (poziom cen {attraction.price_level}/4)."
                        )
        else:
            # Categorical budget validation (legacy)
            budget_price_range = {
                "low": (0, 1),
                "medium": (0, 3),
                "high": (0, 4),
            }
            min_price, max_price = budget_price_range.get(profile.budget.value, (0, 4))

            for day in itinerary.days:
                for attraction in day.attractions:
                    if attraction.price_level is not None:
                        if attraction.price_level > max_price:
                            warnings.append(
                                f"'{attraction.name}' ma poziom cen {attraction.price_level}/4, "
                                f"co przekracza budżet '{profile.budget.value}'."
                            )

        return warnings

    def _validate_opening_hours(self, itinerary: Itinerary) -> list[str]:
        """Validate that attractions are open during scheduled times.

        Args:
            itinerary: Itinerary to validate.

        Returns:
            List of error messages.
        """
        errors: list[str] = []

        for day in itinerary.days:
            current_minutes = _time_to_minutes(day.start_time)

            for i, attraction in enumerate(day.attractions):
                # Check if attraction has opening hours
                if attraction.opening_hours:
                    # Simple check: verify the attraction is generally open
                    # (full day-of-week validation would need the actual trip dates)
                    all_closed = all(
                        "Closed" in v or "Zamknięte" in v
                        for v in attraction.opening_hours.values()
                    )
                    if all_closed:
                        errors.append(
                            f"'{attraction.name}' jest zamknięte we wszystkie dni tygodnia."
                        )

                # Advance time
                current_minutes += attraction.visit_duration_minutes
                if i < len(day.route_segments):
                    current_minutes += day.route_segments[i].duration_minutes

        return errors

    def _check_duplicates(self, itinerary: Itinerary) -> list[str]:
        """Check for duplicate attractions across the itinerary.

        Args:
            itinerary: Itinerary to check.

        Returns:
            List of error messages.
        """
        errors: list[str] = []
        seen_ids: set[str] = set()

        for day in itinerary.days:
            for attraction in day.attractions:
                if attraction.place_id in seen_ids:
                    errors.append(
                        f"Atrakcja '{attraction.name}' pojawia się więcej niż raz w planie."
                    )
                seen_ids.add(attraction.place_id)

        return errors


def _time_to_minutes(time_str: str) -> int:
    """Convert HH:MM time string to minutes since midnight."""
    parts = time_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0
