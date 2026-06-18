"""TravelMind — AI Travel Planner

Main Streamlit application entry point.
"""

import streamlit as st
from ui.quiz_page import render_quiz_page
from ui.results_page import render_results_page
from ui.itinerary_page import render_itinerary_page
from agents.preference_agent import PreferenceAgent
from services.llm import LLMService


def main() -> None:
    """Run the TravelMind application."""
    st.set_page_config(
        page_title="TravelMind — AI Travel Planner",
        page_icon="🌍",
        layout="wide",
    )

    st.title("🌍 TravelMind")
    st.caption("Inteligentny planer podróży z AI")

    # Initialize session state
    if "page" not in st.session_state:
        st.session_state["page"] = "quiz"

    # Initialize services (cached)
    try:
        llm_service = _get_llm_service()
        preference_agent = PreferenceAgent(llm_service)
    except ValueError as e:
        st.error(f"⚠️ Błąd konfiguracji: {str(e)}")
        st.info(
            "Utwórz plik `.env` na podstawie `.env.example` i dodaj klucze API:\n"
            "- `GOOGLE_MAPS_API_KEY` — z Google Cloud Console\n"
            "- `GEMINI_API_KEY` — z Google AI Studio"
        )
        return

    # Sidebar navigation
    with st.sidebar:
        st.header("Nawigacja")
        page = st.radio(
            "Strona",
            options=["quiz", "results", "itinerary"],
            format_func=lambda x: {
                "quiz": "📝 Quiz podróżniczy",
                "results": "🧑‍💼 Profil",
                "itinerary": "🗺️ Plan podróży",
            }.get(x, x),
            key="nav_radio",
            label_visibility="collapsed",
        )

        if page != st.session_state.get("page"):
            st.session_state["page"] = page
            st.rerun()

        st.divider()
        st.markdown(
            "**TravelMind** wykorzystuje AI do tworzenia "
            "spersonalizowanych planów podróży."
        )

    # Render current page
    page = st.session_state.get("page", "quiz")

    if page == "quiz":
        render_quiz_page(preference_agent)
    elif page == "results":
        render_results_page()
    elif page == "itinerary":
        render_itinerary_page()
    else:
        st.session_state["page"] = "quiz"
        st.rerun()


@st.cache_resource
def _get_llm_service() -> LLMService:
    """Get cached LLM service instance."""
    return LLMService()


if __name__ == "__main__":
    main()
