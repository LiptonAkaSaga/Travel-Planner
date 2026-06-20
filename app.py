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
import config


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
    if "selected_model" not in st.session_state:
        st.session_state["selected_model"] = "mimo"

    # Sidebar navigation and settings
    with st.sidebar:
        st.header("⚙️ Ustawienia")

        # Model selector
        model_options = list(config.AVAILABLE_MODELS.keys())
        model_labels = {
            k: v["label"] for k, v in config.AVAILABLE_MODELS.items()
        }
        selected_model = st.selectbox(
            "Model AI",
            options=model_options,
            format_func=lambda x: model_labels.get(x, x),
            index=model_options.index(st.session_state.get("selected_model", "mimo")),
            key="model_select",
        )

        if selected_model != st.session_state.get("selected_model"):
            st.session_state["selected_model"] = selected_model
            # Clear cached services so they re-initialize with new model
            _get_llm_service.clear()
            st.rerun()

        st.divider()
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

    # Initialize services
    try:
        provider = config.AVAILABLE_MODELS[selected_model]["provider"]
        llm_service = _get_llm_service(provider)
        preference_agent = PreferenceAgent(llm_service)
    except ValueError as e:
        st.error(f"⚠️ Błąd konfiguracji: {str(e)}")
        _show_env_help(selected_model)
        return

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


def _show_env_help(selected_model: str) -> None:
    """Show environment setup help based on selected model."""
    if selected_model == "gemini":
        st.info(
            "Utwórz plik `.env` i dodaj:\n"
            "- `GEMINI_API_KEY` — z Google AI Studio\n"
            "- `GOOGLE_MAPS_API_KEY` — z Google Cloud Console"
        )
    else:
        st.info(
            "Utwórz plik `.env` i dodaj:\n"
            "- `OPENAI_API_KEY` — klucz API\n"
            "- `OPENAI_BASE_URL` — adres serwera (opcjonalny)\n"
            "- `GOOGLE_MAPS_API_KEY` — z Google Cloud Console"
        )


@st.cache_resource
def _get_llm_service(provider: str) -> LLMService:
    """Get cached LLM service instance.

    Args:
        provider: 'openai' or 'google'.
    """
    return LLMService(provider=provider)


if __name__ == "__main__":
    main()
