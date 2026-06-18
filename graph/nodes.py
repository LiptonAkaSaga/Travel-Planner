"""Node implementations for the LangGraph travel planning workflow."""

from graph.state import TravelState
from agents.preference_agent import PreferenceAgent
from agents.discovery_agent import DiscoveryAgent
from agents.logistics_agent import LogisticsAgent
from agents.validation_agent import ValidationAgent
from services.google_maps import GoogleMapsService
from services.llm import LLMService


def create_preference_node(
    preference_agent: PreferenceAgent,
):
    """Create the preference assessment node.

    Args:
        preference_agent: The preference agent instance.

    Returns:
        Node function for the graph.
    """
    def preference_node(state: TravelState) -> dict:
        """Process quiz answers and generate travel profile."""
        try:
            profile = preference_agent.generate_profile(state["quiz_answers"])
            return {"profile": profile, "status": "running"}
        except Exception as e:
            return {
                "errors": state.get("errors", []) + [f"Preference Agent error: {str(e)}"],
                "status": "failed",
            }

    return preference_node


def create_discovery_node(
    discovery_agent: DiscoveryAgent,
):
    """Create the discovery node.

    Args:
        discovery_agent: The discovery agent instance.

    Returns:
        Node function for the graph.
    """
    def discovery_node(state: TravelState) -> dict:
        """Discover attractions based on travel profile."""
        try:
            profile = state.get("profile")
            if not profile:
                return {
                    "errors": state.get("errors", []) + ["No travel profile available"],
                    "status": "failed",
                }

            attractions = discovery_agent.discover(
                city=state["city"],
                profile=profile,
                num_days=state["num_days"],
            )

            # Enrich top attractions with descriptions
            enriched: list = []
            for attr in attractions:
                enriched.append(discovery_agent.enrich_attraction(attr))

            return {"attractions": enriched, "status": "running"}
        except Exception as e:
            return {
                "errors": state.get("errors", []) + [f"Discovery Agent error: {str(e)}"],
                "status": "failed",
            }

    return discovery_node


def create_logistics_node(
    logistics_agent: LogisticsAgent,
):
    """Create the logistics node.

    Args:
        logistics_agent: The logistics agent instance.

    Returns:
        Node function for the graph.
    """
    def logistics_node(state: TravelState) -> dict:
        """Optimize routes and create itinerary."""
        try:
            profile = state.get("profile")
            attractions = state.get("attractions", [])

            if not profile:
                return {
                    "errors": state.get("errors", []) + ["No travel profile available"],
                    "status": "failed",
                }

            if not attractions:
                return {
                    "errors": state.get("errors", []) + ["No attractions to plan"],
                    "status": "failed",
                }

            itinerary = logistics_agent.plan_itinerary(
                city=state["city"],
                attractions=attractions,
                num_days=state["num_days"],
                profile=profile,
            )

            return {"itinerary": itinerary, "status": "running"}
        except Exception as e:
            return {
                "errors": state.get("errors", []) + [f"Logistics Agent error: {str(e)}"],
                "status": "failed",
            }

    return logistics_node


def create_validation_node(
    validation_agent: ValidationAgent,
):
    """Create the validation node.

    Args:
        validation_agent: The validation agent instance.

    Returns:
        Node function for the graph.
    """
    def validation_node(state: TravelState) -> dict:
        """Validate the itinerary against guardrails."""
        try:
            itinerary = state.get("itinerary")
            profile = state.get("profile")

            if not itinerary or not profile:
                return {
                    "errors": state.get("errors", []) + ["Missing itinerary or profile for validation"],
                    "status": "failed",
                }

            result = validation_agent.validate(itinerary, profile)

            if result.approved:
                return {
                    "validation_result": result,
                    "status": "completed",
                }
            else:
                return {
                    "validation_result": result,
                    "retry_count": state.get("retry_count", 0) + 1,
                    "status": "running",
                }
        except Exception as e:
            return {
                "errors": state.get("errors", []) + [f"Validation Agent error: {str(e)}"],
                "status": "failed",
            }

    return validation_node
