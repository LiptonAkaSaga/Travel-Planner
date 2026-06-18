"""Preference Agent — travel style assessment and profile generation."""

from models.profile import TravelProfile, TravelStyle, Pace, BudgetLevel
from services.gemini import GeminiService

QUIZ_QUESTIONS: list[dict] = [
    {
        "id": "pace",
        "question": "Jakie jest Twoje preferowane tempo zwiedzania?",
        "options": [
            {"value": "relaxed", "label": "Spokojne — 2-3 atrakcje dziennie, czas na kawę i odpoczynek"},
            {"value": "moderate", "label": "Umiarkowane — 4-5 atrakcji, ale bez pośpiechu"},
            {"value": "intense", "label": "Intensywne — 6+ atrakcji, maksymalnie wykorzystany czas"},
        ],
    },
    {
        "id": "style",
        "question": "Jaki styl podróży najbardziej Ci odpowiada?",
        "options": [
            {"value": "cultural", "label": "Kulturowy — muzea, zabytki, historia"},
            {"value": "adventure", "label": "Przygodowy — aktywności na świeżym powietrzu"},
            {"value": "relaxation", "label": "Relaks — parki, spa, spokojne miejsca"},
            {"value": "foodie", "label": "Kulinarny — lokalna kuchnia, restauracje, street food"},
            {"value": "family", "label": "Rodzinny — atrakcje dla całej rodziny"},
        ],
    },
    {
        "id": "budget",
        "question": "Jaki jest Twój budżet na atrakcje i jedzenie?",
        "options": [
            {"value": "low", "label": "Niski — darmowe atrakcje, street food"},
            {"value": "medium", "label": "Średni — mix płatnych i darmowych, casual dining"},
            {"value": "high", "label": "Wysoki — premium experiences, fine dining"},
        ],
    },
    {
        "id": "categories",
        "question": "Jakie kategorie atrakcji Cię interesują? (wybierz kilka)",
        "options": [
            {"value": "museum", "label": "Muzea i galerie"},
            {"value": "park", "label": "Parki i ogrody"},
            {"value": "landmark", "label": "Zabytki i punkty orientacyjne"},
            {"value": "church", "label": "Kościoły i miejsca kultu"},
            {"value": "restaurant", "label": "Restauracje i kawiarnie"},
            {"value": "shopping", "label": "Zakupy i targi"},
            {"value": "viewpoint", "label": "Punkty widokowe"},
            {"value": "entertainment", "label": "Rozrywka i nocne życie"},
        ],
        "multi": True,
    },
    {
        "id": "interests",
        "question": "Jakie są Twoje główne zainteresowania?",
        "options": [
            {"value": "history", "label": "Historia"},
            {"value": "architecture", "label": "Architektura"},
            {"value": "art", "label": "Sztuka"},
            {"value": "nature", "label": "Natura"},
            {"value": "local_culture", "label": "Lokalna kultura"},
            {"value": "street_food", "label": "Street food"},
            {"value": "nightlife", "label": "Nocne życie"},
            {"value": "photography", "label": "Fotografia"},
        ],
        "multi": True,
    },
    {
        "id": "dietary",
        "question": "Czy masz jakieś ograniczenia dietetyczne?",
        "options": [
            {"value": "none", "label": "Brak"},
            {"value": "vegetarian", "label": "Wegetariańska"},
            {"value": "vegan", "label": "Wegańska"},
            {"value": "halal", "label": "Halal"},
            {"value": "kosher", "label": "Koszerna"},
            {"value": "gluten_free", "label": "Bezglutenowa"},
        ],
        "multi": True,
    },
]


class PreferenceAgent:
    """Agent responsible for travel style assessment and profile generation."""

    def __init__(self, gemini_service: GeminiService) -> None:
        self._gemini = gemini_service

    def get_quiz_questions(self) -> list[dict]:
        """Return the quiz questions for the user.

        Returns:
            List of question dictionaries with id, question, options.
        """
        return QUIZ_QUESTIONS

    def generate_profile(self, answers: dict[str, list[str] | str]) -> TravelProfile:
        """Generate a TravelProfile from quiz answers.

        Args:
            answers: Dictionary mapping question IDs to selected values.

        Returns:
            TravelProfile generated from the answers.
        """
        system_prompt = """You are a travel personality analyst. Based on the user's quiz answers,
generate a travel profile. You MUST return a JSON object with exactly these fields:

{
    "style": one of ["cultural", "adventure", "relaxation", "foodie", "nightlife", "family", "budget", "luxury"],
    "pace": one of ["relaxed", "moderate", "intense"],
    "budget": one of ["low", "medium", "high"],
    "preferred_categories": list of category strings from the answers,
    "avoid_categories": list of categories to avoid (infer from what was NOT selected),
    "interests": list of interest strings from the answers,
    "dietary_restrictions": list of dietary restriction strings (empty list if none),
    "mobility_notes": string with any mobility notes (empty string if none),
    "summary": one-paragraph human-readable summary in Polish describing the travel personality
}

IMPORTANT: Return ONLY valid JSON, no markdown, no explanation."""

        user_message = f"Quiz answers:\n{_format_answers(answers)}"

        result = self._gemini.chat(system_prompt, user_message)

        # Parse the JSON response
        import json

        try:
            # Try to extract JSON from the response
            json_str = result.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            data = json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            # Fallback: build profile directly from answers
            data = _build_fallback_profile(answers)

        return TravelProfile(**data)


def _format_answers(answers: dict[str, list[str] | str]) -> str:
    """Format quiz answers for the LLM prompt."""
    lines: list[str] = []
    for q in QUIZ_QUESTIONS:
        qid = q["id"]
        if qid in answers:
            val = answers[qid]
            if isinstance(val, list):
                val_str = ", ".join(val)
            else:
                val_str = str(val)
            lines.append(f"- {q['question']}: {val_str}")
    return "\n".join(lines)


def _build_fallback_profile(answers: dict[str, list[str] | str]) -> dict:
    """Build a fallback profile from answers without LLM."""
    style_raw = answers.get("style", "cultural")
    style = style_raw if isinstance(style_raw, str) else "cultural"

    pace_raw = answers.get("pace", "moderate")
    pace = pace_raw if isinstance(pace_raw, str) else "moderate"

    budget_raw = answers.get("budget", "medium")
    budget = budget_raw if isinstance(budget_raw, str) else "medium"

    categories = answers.get("categories", ["landmark", "museum"])
    if not isinstance(categories, list):
        categories = [categories]

    interests = answers.get("interests", ["history"])
    if not isinstance(interests, list):
        interests = [interests]

    dietary = answers.get("dietary", [])
    if not isinstance(dietary, list):
        dietary = [dietary]
    dietary = [d for d in dietary if d != "none"]

    return {
        "style": style,
        "pace": pace,
        "budget": budget,
        "preferred_categories": categories,
        "avoid_categories": [],
        "interests": interests,
        "dietary_restrictions": dietary,
        "mobility_notes": "",
        "summary": f"Podróżnik preferujący styl {style} w tempie {pace}.",
    }
