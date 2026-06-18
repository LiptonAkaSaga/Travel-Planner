"""Results page — travel profile display."""

import streamlit as st
from models.profile import TravelProfile


def render_results_page() -> None:
    """Render the travel profile results page."""
    profile: TravelProfile | None = st.session_state.get("profile")

    if not profile:
        st.warning("Najpierw wypełnij quiz podróżniczy.")
        st.session_state["page"] = "quiz"
        st.rerun()
        return

    st.header("🧑‍💼 Twój Profil Podróżniczy")

    # Summary card
    st.info(profile.summary)

    # Profile details in columns
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Styl podróży")
        style_labels = {
            "cultural": "🏛️ Kulturowy",
            "adventure": "🧗 Przygodowy",
            "relaxation": "🧘 Relaks",
            "foodie": "🍽️ Kulinarny",
            "nightlife": "🌙 Nocne życie",
            "family": "👨‍👩‍👧‍👦 Rodzinny",
            "budget": "💰 Budżetowy",
            "luxury": "✨ Luksusowy",
        }
        st.markdown(f"**{style_labels.get(profile.style.value, profile.style.value)}**")

        st.subheader("Tempo")
        pace_labels = {
            "relaxed": "🐌 Spokojne (2-3 atrakcje/dzień)",
            "moderate": "🚶 Umiarkowane (4-5 atrakcji/dzień)",
            "intense": "🏃 Intensywne (6+ atrakcji/dzień)",
        }
        st.markdown(f"**{pace_labels.get(profile.pace.value, profile.pace.value)}**")

        st.subheader("Budżet")
        budget_labels = {
            "low": "💚 Niski",
            "medium": "💛 Średni",
            "high": "❤️ Wysoki",
        }
        st.markdown(f"**{budget_labels.get(profile.budget.value, profile.budget.value)}**")

    with col2:
        st.subheader("Preferowane kategorie")
        for cat in profile.preferred_categories:
            st.markdown(f"- {cat}")

        if profile.avoid_categories:
            st.subheader("Unikane kategorie")
            for cat in profile.avoid_categories:
                st.markdown(f"- {cat}")

        st.subheader("Zainteresowania")
        for interest in profile.interests:
            st.markdown(f"- {interest}")

    if profile.dietary_restrictions:
        st.subheader("Ograniczenia dietetyczne")
        st.markdown(", ".join(profile.dietary_restrictions))

    # Navigation
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Wypełnij quiz ponownie"):
            st.session_state["page"] = "quiz"
            st.rerun()

    with col2:
        if st.button("🗺️ Stwórz plan podróży", type="primary"):
            st.session_state["page"] = "itinerary"
            st.rerun()
