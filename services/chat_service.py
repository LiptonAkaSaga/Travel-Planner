"""Chat service — conversational travel planning assistant."""

import json
import logging
from services.llm import LLMService
from models.profile import TravelProfile, TravelStyle, Pace, BudgetLevel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Jesteś TravelMind — sympatyczny i pomocny asystent podróży AI.

Twoim celem jest zebranie informacji o podróży użytkownika poprzez naturalną rozmowę.

Pytaj o:
1. Dokąd użytkownik chce jechać (miasto/destynacja)
2. Ile dni planuje wyjazd
3. Jaki ma budżet na cały wyjazd (w PLN)
4. Co go interesuje (zabytki, muzea, natura, jedzenie, rozrywka itp.)
5. Jaki styl podróży preferuje (aktywny, relaks, kulturalny, kulinarny)
6. Jak wyglądały jego ostatnie wakacje — co mu się podobało, a co nie
7. Ograniczenia dietetyczne
8. Ile posiłków dziennie chce jeść w restauracji (śniadanie, obiad, kolacja)

ZASADY:
- Pytaj po jednym-dwa pytania na raz, nie wypisuj wszystkiego naraz
- Bądź ciepły, naturalny, używaj emoji
- Odpowiadaj po polsku
- Nie powtarzaj pytań, na które użytkownik już odpowiedział
- Słuchaj odpowiedzi i dostosowuj kolejne pytania
- Gdy masz wystarczająco dużo informacji, powiedz użytkownikowi że może nacisnąć przycisk "Podsumuj rozmowę i stwórz plan"

Rozpocznij rozmowę od krótkiego powitania i pierwszego pytania."""


SUMMARIZE_PROMPT = """Przeanalizuj poniższą rozmowę z użytkownikiem i wyciągnij z niej informacje o podróży.

Zwróć JSON z następującymi polami:
{
    "city": "nazwa miasta",
    "num_days": liczba_dni,
    "budget_amount": budżet_w_PLN_lub_null,
    "style": jeden_z ["cultural", "adventure", "relaxation", "foodie", "nightlife", "family", "budget", "luxury"],
    "pace": jeden_z ["relaxed", "moderate", "intense"],
    "budget": jeden_z ["low", "medium", "high"],
    "preferred_categories": ["lista", "kategorii"],
    "interests": ["lista", "zainteresowań"],
    "dietary_restrictions": ["lista", "ograniczeń"],
    "meal_preferences": {"breakfast": 0_lub_1, "lunch": 0_lub_1, "dinner": 0_lub_1},
    "summary": "jednozdaniowe podsumowanie profilu podróżniczego po polsku"
}

WAŻNE:
- city MUSI być podane (jeśli nie wiadomo, zwróć null)
- Jeśli użytkownik nie podał budżetu, budget_amount = null
- Jeśli użytkownik nie mówił o posiłkach, domyślnie lunch=1
- Kategorie mogą być: museum, park, landmark, church, restaurant, shopping, viewpoint, entertainment
- Zainteresowania mogą być: history, architecture, art, nature, local_culture, street_food, nightlife, photography

Zwróć TYLKO valid JSON, bez markdown."""


class ChatService:
    """Service for conversational travel planning."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service
        self._history: list[dict[str, str]] = []

    @property
    def history(self) -> list[dict[str, str]]:
        """Return chat history."""
        return list(self._history)

    def send_message(self, user_message: str) -> str:
        """Send a message and get a response with conversation context.

        Args:
            user_message: User's message text.

        Returns:
            Assistant's response text.
        """
        self._history.append({"role": "user", "content": user_message})

        # Build messages for LLM
        messages_text = self._format_history()

        try:
            response = self._llm.chat(SYSTEM_PROMPT, messages_text)
            self._history.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            logger.error(f"Chat error: {e}")
            error_msg = "Przepraszam, wystąpił błąd. Spróbuj ponownie."
            self._history.append({"role": "assistant", "content": error_msg})
            return error_msg

    def summarize_to_plan(self) -> dict:
        """Summarize the conversation and extract trip parameters.

        Returns:
            Dictionary with trip parameters (city, num_days, budget_amount, etc.)
        """
        if not self._history:
            raise ValueError("Brak rozmowy do podsumowania")

        messages_text = self._format_history()

        try:
            result = self._llm.chat(SUMMARIZE_PROMPT, messages_text)

            # Parse JSON
            json_str = result.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]

            data = json.loads(json_str)
            logger.info(f"Chat summary extracted: city={data.get('city')}, days={data.get('num_days')}")
            return data

        except Exception as e:
            logger.error(f"Chat summary error: {e}")
            raise ValueError(f"Nie udało się podsumować rozmowy: {e}")

    def build_profile_from_summary(self, summary: dict) -> TravelProfile:
        """Build a TravelProfile from conversation summary.

        Args:
            summary: Dictionary from summarize_to_plan().

        Returns:
            TravelProfile object.
        """
        return TravelProfile(
            style=TravelStyle(summary.get("style", "cultural")),
            pace=Pace(summary.get("pace", "moderate")),
            budget=BudgetLevel(summary.get("budget", "medium")),
            budget_amount=summary.get("budget_amount"),
            preferred_categories=summary.get("preferred_categories", ["landmark", "museum"]),
            interests=summary.get("interests", ["history"]),
            dietary_restrictions=summary.get("dietary_restrictions", []),
            meal_preferences=summary.get("meal_preferences", {"lunch": 1}),
            summary=summary.get("summary", "Profil wygenerowany z rozmowy."),
        )

    def clear(self) -> None:
        """Clear chat history."""
        self._history = []

    def _format_history(self) -> str:
        """Format chat history as a single prompt for the LLM."""
        lines = []
        for msg in self._history:
            role = "Użytkownik" if msg["role"] == "user" else "TravelMind"
            lines.append(f"{role}: {msg['content']}")
        return "\n\n".join(lines)
