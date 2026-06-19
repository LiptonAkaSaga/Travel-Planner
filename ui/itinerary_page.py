"""Itinerary page — trip planning and results display."""

import streamlit as st
from models.profile import TravelProfile
from models.itinerary import Itinerary
from models.meal import MEAL_LABELS, MEAL_ICONS, MealType
from graph.builder import build_travel_graph, create_initial_state
from services.google_maps import GoogleMapsService
from services.llm import LLMService
from ui.map_component import render_map


def render_itinerary_page() -> None:
    """Render the itinerary planning and results page."""
    profile: TravelProfile | None = st.session_state.get("profile")

    if not profile:
        st.warning("Najpierw wypełnij quiz podróżniczy.")
        st.session_state["page"] = "quiz"
        st.rerun()
        return

    st.header("🗺️ Plan Podróży")

    # City, days, and budget input
    col1, col2, col3 = st.columns(3)
    with col1:
        city = st.text_input("🏙️ Miasto docelowe", value=st.session_state.get("city", "Kraków"))
    with col2:
        num_days = st.number_input(
            "📅 Liczba dni",
            min_value=1,
            max_value=14,
            value=st.session_state.get("num_days", 3),
        )
    with col3:
        budget_amount = st.number_input(
            "💰 Budżet (PLN)",
            min_value=0,
            max_value=100000,
            step=100,
            value=int(st.session_state.get("budget_amount", 0)),
            help="Całkowity budżet na wyjazd w PLN. 0 = bez limitu.",
        )

    # Generate button
    if st.button("✨ Generuj plan podróży", type="primary"):
        if not city.strip():
            st.error("Proszę podać nazwę miasta.")
            return

        st.session_state["city"] = city
        st.session_state["num_days"] = num_days
        st.session_state["budget_amount"] = budget_amount

        # Get meal preferences from profile or quiz
        meal_preferences = {}
        if profile and hasattr(profile, "meal_preferences"):
            meal_preferences = profile.meal_preferences
        elif "quiz_answers" in st.session_state:
            meals_raw = st.session_state["quiz_answers"].get("meals", [])
            if isinstance(meals_raw, list):
                meal_preferences = {
                    "breakfast": 1 if "breakfast" in meals_raw else 0,
                    "lunch": 1 if "lunch" in meals_raw else 0,
                    "dinner": 1 if "dinner" in meals_raw else 0,
                }

        with st.spinner("Generuję plan podróży... To może chwilę zająć."):
            try:
                # Initialize services
                maps_service = GoogleMapsService()
                llm_service = LLMService()

                # Build and run the graph
                graph = build_travel_graph(maps_service, llm_service)
                initial_state = create_initial_state(
                    city=city,
                    num_days=num_days,
                    budget=0,
                    quiz_answers=st.session_state.get("quiz_answers", {}),
                    budget_amount=budget_amount if budget_amount > 0 else None,
                    meal_preferences=meal_preferences,
                    chat_context=st.session_state.get("chat_context", ""),
                    country=st.session_state.get("country", ""),
                )

                # Override profile in state
                initial_state["profile"] = profile

                result = graph.invoke(initial_state)

                # Store results
                st.session_state["itinerary"] = result.get("itinerary")
                st.session_state["validation"] = result.get("validation_result")
                st.session_state["errors"] = result.get("errors", [])

                if result.get("status") == "failed":
                    st.error("Wystąpił błąd podczas generowania planu.")
                    for err in result.get("errors", []):
                        st.error(f"• {err}")
                elif result.get("itinerary"):
                    st.success("Plan podróży wygenerowany!")
                else:
                    st.warning("Nie udało się wygenerować planu. Spróbuj ponownie.")

            except ValueError as e:
                st.error(f"Błąd konfiguracji: {str(e)}")
                st.info("Upewnij się, że klucze API są ustawione w pliku .env")
            except Exception as e:
                st.error(f"Nieoczekiwany błąd: {str(e)}")

    # Display results if available
    itinerary: Itinerary | None = st.session_state.get("itinerary")
    if itinerary:
        _display_itinerary(itinerary)


def _display_itinerary(itinerary: Itinerary) -> None:
    """Display the generated itinerary.

    Args:
        itinerary: The itinerary to display.
    """
    st.divider()
    st.header(f"📋 Plan: {itinerary.city} ({itinerary.num_days} dni)")

    # Summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Atrakcje", itinerary.total_attractions)
    with col2:
        st.metric("Dni", itinerary.num_days)
    with col3:
        hours = itinerary.total_travel_minutes / 60
        st.metric("Czas podróży", f"{hours:.1f}h")

    # Map
    st.subheader("🗺️ Mapa trasy")
    render_map(itinerary)

    # Daily plans
    for day in itinerary.days:
        with st.expander(f"📅 Dzień {day.day_number} ({day.start_time} — {day.end_time})", expanded=True):
            # Day stats
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"🕐 Zwiedzanie: {day.total_visit_minutes} min")
            with col2:
                st.caption(f"🚶 Podróż: {day.total_travel_minutes} min")

            # Build timeline: interleave meals and attractions by time
            timeline: list[tuple[str, object]] = []

            # Add meals to timeline
            for meal in day.meals:
                timeline.append(("meal", meal))

            # Add attractions to timeline
            for i, attr in enumerate(day.attractions):
                timeline.append(("attraction", (i, attr)))

            # Sort by scheduled time (meals) or order (attractions)
            # Simple approach: breakfast before attractions, lunch in middle, dinner after
            def _sort_key(item):
                kind, data = item
                if kind == "meal":
                    return (0, data.scheduled_time)
                else:
                    return (1, f"{data[0]:03d}")

            timeline.sort(key=_sort_key)

            # Display timeline
            meal_idx = 0
            attr_idx = 0
            for kind, data in timeline:
                if kind == "meal":
                    meal = data
                    icon = MEAL_ICONS.get(meal.meal_type, "🍽️")
                    label = MEAL_LABELS.get(meal.meal_type, "Posiłek")
                    with st.container():
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.markdown(f"**{icon}**")
                            st.markdown(f"⭐ {meal.rating}/5" if meal.rating else "")
                        with col2:
                            st.markdown(f"### {icon} {label}")
                            st.caption(f"🕐 {meal.scheduled_time} ({meal.duration_minutes} min)")
                            st.caption(f"📍 {meal.restaurant_name}")
                            if meal.restaurant_address:
                                st.caption(meal.restaurant_address)
                            if meal.description:
                                st.markdown(meal.description)
                        st.divider()
                else:
                    i, attr = data
                    with st.container():
                        col1, col2 = st.columns([1, 3])

                        with col1:
                            st.markdown(f"**{i + 1}.**")
                            st.markdown(f"⭐ {attr.rating}/5")

                        with col2:
                            st.markdown(f"### {attr.name}")
                            st.caption(f"📍 {attr.address}")
                            st.caption(f"⏱️ {attr.visit_duration_minutes} min")

                            if attr.description:
                                st.markdown(attr.description)

                            if attr.opening_hours:
                                with st.popover("🕐 Godziny otwarcia"):
                                    for day_name, hours in attr.opening_hours.items():
                                        st.text(f"{day_name}: {hours}")

                        # Route to next attraction
                        if i < len(day.route_segments):
                            seg = day.route_segments[i]
                            st.caption(
                                f"🚶 {seg.duration_minutes} min do {seg.to_name} "
                                f"({seg.distance_meters}m)"
                            )

                        st.divider()

    # Validation warnings
    validation = st.session_state.get("validation")
    if validation and validation.warnings:
        st.subheader("⚠️ Ostrzeżenia")
        for warning in validation.warnings:
            st.warning(warning)

    # Errors
    errors = st.session_state.get("errors", [])
    if errors:
        st.subheader("❌ Błędy")
        for error in errors:
            st.error(error)
