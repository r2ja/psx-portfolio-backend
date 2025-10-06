"""Agent state definitions."""

from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State for the portfolio management agent."""
    messages: Annotated[List[Dict[str, Any]], add_messages]
    user_query: str
    portfolio: List[Dict[str, Any]]  # User's portfolio
    analysis_result: Dict[str, Any]
    next_action: str
