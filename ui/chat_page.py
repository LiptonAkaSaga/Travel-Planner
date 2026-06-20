"""Chat page — conversational travel planning assistant."""

import streamlit as st
from services.chat_service import ChatService
from services.llm import LLMService


def render_chat_page(llm_service: LLMService) -> None:
    """Render the chat-based travel planning page.

    Args:
        llm_service: LLM service instance.
    """
    st.header("💬 Porozmawiajmy o Twojej podróży")
    st.caption(
        "Opowiedz mi o swoich planach podróżniczych, a pomogę Ci stworzyć idealny plan!"
    )

    # Initialize chat service in session state
    if "chat_service" not in st.session_state:
        st.session_state["chat_service"] = ChatService(llm_service)

    chat_service: ChatService = st.session_state["chat_service"]

    # Display chat history
    for msg in chat_service.history:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])

    # Welcome message if empty chat
    if not chat_service.history:
        with st.chat_message("assistant"):
            welcome = (
                "Cześć! 👋 Jestem TravelMind, Twój asystent podróży AI.\n\n"
                "Pomogę Ci zaplanować idealny wyjazd. Powiedz mi:\n"
                "- 🏙️ Dokąd chcesz jechać?\n"
                "- 📅 Na ile dni?\n"
                "- 💰 Jaki masz budżet?\n\n"
                "Możesz też opowiedzieć mi o swoich zainteresowaniach "
                "i jak wyglądały Twoje ostatnie wakacje! 🌍"
            )
            st.markdown(welcome)

    # Chat input
    if user_input := st.chat_input("Napisz o swoich planach podróżniczych..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Myślę..."):
                response = chat_service.send_message(user_input)
            st.markdown(response)

        st.rerun()

    # Action buttons
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🗑️ Wyczyść rozmowę", use_container_width=True):
            chat_service.clear()
            st.rerun()

    with col2:
        if st.button(
            "📋 Podsumuj rozmowę i stwórz plan",
            type="primary",
            use_container_width=True,
            disabled=len(chat_service.history) < 2,
        ):
            _handle_summarize(chat_service)

    with col3:
        if st.button("📝 Szybki quiz", use_container_width=True):
            st.session_state["page"] = "quiz"
            st.rerun()


def _handle_summarize(chat_service: ChatService) -> None:
    """Handle the summarize and create plan action."""
    with st.spinner("Podsumowuję rozmowę i przygotowuję plan..."):
        try:
            summary = chat_service.summarize_to_plan()

            # Validate required fields
            city = summary.get("city")
            if not city:
                st.error(
                    "Nie udało się określić miasta docelowego. "
                    "Wróć do rozmowy i podaj dokąd chcesz jechać."
                )
                return

            num_days = summary.get("num_days", 3)
            if not num_days or num_days < 1:
                num_days = 3

            # Build profile
            profile = chat_service.build_profile_from_summary(summary)

            # Store in session state
            st.session_state["profile"] = profile
            st.session_state["quiz_answers"] = {
                "style": summary.get("style", "cultural"),
                "pace": summary.get("pace", "moderate"),
                "budget": summary.get("budget", "medium"),
                "budget_amount": summary.get("budget_amount", 0),
                "categories": summary.get("preferred_categories", []),
                "interests": summary.get("interests", []),
                "dietary": summary.get("dietary_restrictions", []),
                "meals": [
                    mt for mt, count in summary.get("meal_preferences", {}).items()
                    if count > 0
                ],
            }
            st.session_state["city"] = city
            st.session_state["country"] = summary.get("country", "")
            st.session_state["num_days"] = num_days
            st.session_state["budget_amount"] = summary.get("budget_amount", 0)
            st.session_state["meal_preferences"] = summary.get(
                "meal_preferences", {"lunch": 1}
            )
            st.session_state["chat_context"] = _format_chat_context(chat_service)

            # Store day constraints (convert string keys to int)
            raw_constraints = summary.get("day_constraints", {})
            st.session_state["day_constraints"] = {
                int(k): v for k, v in raw_constraints.items()
            } if raw_constraints else {}

            st.success(
                f"Podsumowanie gotowe! 🎉\n\n"
                f"**Miasto:** {city}\n"
                f"**Dni:** {num_days}\n"
                f"**Budżet:** {summary.get('budget_amount', 'nie podano')} PLN\n\n"
                f"Przechodzę do generowania planu..."
            )

            st.session_state["page"] = "itinerary"
            st.rerun()

        except ValueError as e:
            st.error(f"Błąd podsumowania: {str(e)}")
        except Exception as e:
            st.error(f"Nieoczekiwany błąd: {str(e)}")


def _format_chat_context(chat_service: ChatService) -> str:
    """Format chat history as context string for the planning agents."""
    lines = []
    for msg in chat_service.history:
        role = "Użytkownik" if msg["role"] == "user" else "TravelMind"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)
