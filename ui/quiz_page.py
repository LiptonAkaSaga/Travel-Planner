"""Quiz page — travel personality assessment."""

import streamlit as st
from agents.preference_agent import PreferenceAgent, QUIZ_QUESTIONS


def render_quiz_page(preference_agent: PreferenceAgent) -> None:
    """Render the travel personality quiz page.

    Args:
        preference_agent: The preference agent for generating profiles.
    """
    st.header("🌍 Quiz Podróżniczy")
    st.markdown(
        "Odpowiedz na kilka pytań, a stworzymy Twój profil podróżniczy "
        "i dopasujemy plan podróży do Twoich preferencji."
    )

    answers: dict[str, list[str] | str] = {}

    with st.form("travel_quiz"):
        for question in QUIZ_QUESTIONS:
            qid = question["id"]
            st.subheader(question["question"])

            options = [opt["label"] for opt in question["options"]]
            value_map = {opt["label"]: opt["value"] for opt in question["options"]}

            if question.get("multi"):
                # Multi-select
                selected_labels = st.multiselect(
                    label=question["question"],
                    options=options,
                    key=f"quiz_{qid}",
                    label_visibility="collapsed",
                )
                answers[qid] = [value_map[label] for label in selected_labels]
            else:
                # Single-select radio
                selected_label = st.radio(
                    label=question["question"],
                    options=options,
                    key=f"quiz_{qid}",
                    label_visibility="collapsed",
                )
                answers[qid] = value_map.get(selected_label, "")

        submitted = st.form_submit_button("🎯 Generuj profil podróżniczy", type="primary")

    if submitted:
        # Validate at least basic answers
        if not answers.get("style") or not answers.get("pace"):
            st.error("Proszę odpowiedzieć na pytania o styl i tempo podróży.")
            return

        categories = answers.get("categories", [])
        if not categories or (isinstance(categories, list) and len(categories) == 0):
            st.error("Proszę wybrać przynajmniej jedną kategorię atrakcji.")
            return

        with st.spinner("Generuję Twój profil podróżniczy..."):
            try:
                profile = preference_agent.generate_profile(answers)
                st.session_state["profile"] = profile
                st.session_state["quiz_answers"] = answers
                st.session_state["page"] = "results"
                st.rerun()
            except Exception as e:
                st.error(f"Błąd podczas generowania profilu: {str(e)}")
