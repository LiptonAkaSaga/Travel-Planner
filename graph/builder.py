"""LangGraph workflow builder for travel planning."""

from typing import Literal
from langgraph.graph import StateGraph, START, END

from graph.state import TravelState
from graph.nodes import (
    create_preference_node,
    create_discovery_node,
    create_logistics_node,
    create_validation_node,
)
from agents.preference_agent import PreferenceAgent
from agents.discovery_agent import DiscoveryAgent
from agents.logistics_agent import LogisticsAgent
from agents.validation_agent import ValidationAgent
from services.google_maps import GoogleMapsService
from services.llm import LLMService
import config


def build_travel_graph(
    maps_service: GoogleMapsService,
    llm_service: LLMService,
) -> StateGraph:
    """Build the LangGraph workflow for travel planning.

    The graph flow:
    START → preference → discovery → logistics → validation
                                                  ↓
                                            (if rejected and retries < max)
                                                  → logistics (retry)
                                            (if approved or max retries)
                                                  → END

    Args:
        maps_service: Google Maps service instance.
        llm_service: LLM service instance.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    # Create agents
    preference_agent = PreferenceAgent(llm_service)
    discovery_agent = DiscoveryAgent(maps_service, llm_service)
    logistics_agent = LogisticsAgent(maps_service)
    validation_agent = ValidationAgent(maps_service)

    # Create node functions
    preference_node = create_preference_node(preference_agent)
    discovery_node = create_discovery_node(discovery_agent)
    logistics_node = create_logistics_node(logistics_agent)
    validation_node = create_validation_node(validation_agent)

    # Define routing function
    def after_validation(state: TravelState) -> Literal["logistics_node", "__end__"]:
        """Route after validation: retry or end."""
        # Check for fatal errors
        if state.get("status") == "failed":
            return "__end__"

        validation = state.get("validation_result")
        if validation and validation.approved:
            return "__end__"

        # Check retry count
        retry_count = state.get("retry_count", 0)
        if retry_count >= config.MAX_RETRIES:
            return "__end__"

        # Retry logistics
        return "logistics_node"

    def check_status(state: TravelState) -> Literal["discovery_node", "__end__"]:
        """Check if we should continue after preference node."""
        if state.get("status") == "failed":
            return "__end__"
        return "discovery_node"

    def check_discovery(state: TravelState) -> Literal["logistics_node", "__end__"]:
        """Check if we should continue after discovery node."""
        if state.get("status") == "failed":
            return "__end__"
        return "logistics_node"

    # Build the graph
    graph_builder = StateGraph(TravelState)

    # Add nodes
    graph_builder.add_node("preference_node", preference_node)
    graph_builder.add_node("discovery_node", discovery_node)
    graph_builder.add_node("logistics_node", logistics_node)
    graph_builder.add_node("validation_node", validation_node)

    # Add edges
    graph_builder.add_edge(START, "preference_node")
    graph_builder.add_conditional_edges("preference_node", check_status)
    graph_builder.add_conditional_edges("discovery_node", check_discovery)
    graph_builder.add_edge("logistics_node", "validation_node")
    graph_builder.add_conditional_edges("validation_node", after_validation)

    return graph_builder.compile()


def create_initial_state(
    city: str,
    num_days: int,
    budget: float,
    quiz_answers: dict[str, list[str] | str],
    budget_amount: float | None = None,
    meal_preferences: dict[str, int] | None = None,
    chat_context: str = "",
) -> TravelState:
    """Create the initial state for the travel planning graph.

    Args:
        city: Target city name.
        num_days: Number of trip days.
        budget: Trip budget level (legacy).
        quiz_answers: User's quiz answers.
        budget_amount: Numeric budget in PLN for the entire trip.
        meal_preferences: Meal counts per day (breakfast, lunch, dinner).
        chat_context: Context from chat conversation.

    Returns:
        Initial TravelState dictionary.
    """
    return TravelState(
        city=city,
        num_days=num_days,
        budget=budget,
        budget_amount=budget_amount,
        quiz_answers=quiz_answers,
        profile=None,
        attractions=[],
        restaurants={},
        itinerary=None,
        validation_result=None,
        place_details_cache={},
        meal_preferences=meal_preferences or {},
        chat_context=chat_context,
        retry_count=0,
        errors=[],
        status="running",
    )
