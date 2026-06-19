"""TravelMind — AI Travel Planner

Main Streamlit application entry point.
"""

import logging
import streamlit as st

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
from ui.quiz_page import render_quiz_page
from ui.results_page import render_results_page
from ui.itinerary_page import render_itinerary_page
from ui.chat_page import render_chat_page
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
        st.session_state["page"] = "chat"

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
            options=["chat", "quiz", "results", "itinerary"],
            format_func=lambda x: {
                "chat": "💬 Rozmowa z AI",
                "quiz": "📝 Szybki quiz",
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
    page = st.session_state.get("page", "chat")

    if page == "chat":
        render_chat_page(llm_service)
    elif page == "quiz":
        render_quiz_page(preference_agent)
    elif page == "results":
        render_results_page()
    elif page == "itinerary":
        render_itinerary_page()
    else:
        st.session_state["page"] = "chat"
        st.rerun()


@st.cache_resource
def _get_llm_service() -> LLMService:
    """Get cached LLM service instance."""
    return LLMService()


if __name__ == "__main__":
    main()
