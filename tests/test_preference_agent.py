"""Tests for the Preference Agent."""

import json
from unittest.mock import MagicMock
from agents.preference_agent import PreferenceAgent, _build_fallback_profile
from models.profile import TravelProfile


class TestPreferenceAgent:
    """Test suite for PreferenceAgent."""

    def _make_agent(self, response: str = "") -> tuple[PreferenceAgent, MagicMock]:
        """Create a PreferenceAgent with mocked Gemini service."""
        mock_gemini = MagicMock()
        if response:
            mock_gemini.chat.return_value = response
        return PreferenceAgent(mock_gemini), mock_gemini

    def test_get_quiz_questions_returns_list(self):
        agent, _ = self._make_agent()
        questions = agent.get_quiz_questions()
        assert isinstance(questions, list)
        assert len(questions) >= 5

    def test_get_quiz_questions_have_required_fields(self):
        agent, _ = self._make_agent()
        for q in agent.get_quiz_questions():
            assert "id" in q
            assert "question" in q
            assert "options" in q
            assert len(q["options"]) >= 2

    def test_generate_profile_from_json_response(self):
        profile_json = json.dumps({
            "style": "cultural",
            "pace": "moderate",
            "budget": "medium",
            "preferred_categories": ["museum", "landmark"],
            "avoid_categories": [],
            "interests": ["history", "architecture"],
            "dietary_restrictions": [],
            "mobility_notes": "",
            "summary": "Podróżnik kulturalny w umiarkowanym tempie.",
        })
        agent, mock_gemini = self._make_agent(profile_json)

        answers = {
            "style": "cultural",
            "pace": "moderate",
            "budget": "medium",
            "categories": ["museum", "landmark"],
            "interests": ["history", "architecture"],
            "dietary": ["none"],
        }

        profile = agent.generate_profile(answers)
        assert isinstance(profile, TravelProfile)
        assert profile.style.value == "cultural"
        assert profile.pace.value == "moderate"
        assert "museum" in profile.preferred_categories

    def test_generate_profile_fallback_on_invalid_json(self):
        agent, _ = self._make_agent("this is not json")

        answers = {
            "style": "adventure",
            "pace": "intense",
            "budget": "low",
            "categories": ["park"],
            "interests": ["nature"],
            "dietary": ["none"],
        }

        profile = agent.generate_profile(answers)
        assert isinstance(profile, TravelProfile)
        assert profile.style.value == "adventure"

    def test_generate_profile_gemini_called(self):
        profile_json = json.dumps({
            "style": "foodie",
            "pace": "relaxed",
            "budget": "high",
            "preferred_categories": ["restaurant"],
            "avoid_categories": [],
            "interests": ["street_food"],
            "dietary_restrictions": [],
            "mobility_notes": "",
            "summary": "Foodie traveler.",
        })
        agent, mock_gemini = self._make_agent(profile_json)

        answers = {"style": "foodie", "pace": "relaxed", "budget": "high",
                   "categories": ["restaurant"], "interests": ["street_food"],
                   "dietary": ["none"]}
        agent.generate_profile(answers)

        mock_gemini.chat.assert_called_once()


class TestFallbackProfile:
    """Test the fallback profile builder."""

    def test_fallback_with_all_answers(self):
        answers = {
            "style": "cultural",
            "pace": "moderate",
            "budget": "medium",
            "categories": ["museum", "landmark"],
            "interests": ["history"],
            "dietary": ["vegetarian"],
        }
        result = _build_fallback_profile(answers)
        assert result["style"] == "cultural"
        assert result["pace"] == "moderate"
        assert "museum" in result["preferred_categories"]
        assert "vegetarian" in result["dietary_restrictions"]

    def test_fallback_filters_none_dietary(self):
        answers = {
            "style": "cultural",
            "pace": "moderate",
            "budget": "medium",
            "categories": ["museum"],
            "interests": ["history"],
            "dietary": ["none"],
        }
        result = _build_fallback_profile(answers)
        assert result["dietary_restrictions"] == []

    def test_fallback_with_missing_answers(self):
        answers: dict = {}
        result = _build_fallback_profile(answers)
        assert result["style"] == "cultural"  # default
        assert result["pace"] == "moderate"  # default
