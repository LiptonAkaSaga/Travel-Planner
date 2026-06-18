"""Itinerary page — trip planning and results display."""

import streamlit as st
from models.profile import TravelProfile
from models.itinerary import Itinerary
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

    # City and days input
    col1, col2 = st.columns(2)
    with col1:
        city = st.text_input("🏙️ Miasto docelowe", value=st.session_state.get("city", "Kraków"))
    with col2:
        num_days = st.number_input(
            "📅 Liczba dni",
            min_value=1,
            max_value=14,
            value=st.session_state.get("num_days", 3),
        )

    # Generate button
    if st.button("✨ Generuj plan podróży", type="primary"):
        if not city.strip():
            st.error("Proszę podać nazwę miasta.")
            return

        st.session_state["city"] = city
        st.session_state["num_days"] = num_days

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

            # Attractions
            for i, attr in enumerate(day.attractions):
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

                    # Route to next
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
