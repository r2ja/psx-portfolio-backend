"""Main portfolio management agent using LangGraph."""

import os
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from .state import AgentState
from tools.tradingview_tools import TRADINGVIEW_TOOLS


class PortfolioAgent:
    """LangGraph-based portfolio management agent."""

    def __init__(self, api_key: str = None):
        """Initialize the agent with OpenAI."""
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Cheap and fast
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            temperature=0.7
        )

        # Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(TRADINGVIEW_TOOLS)

        # Create the graph
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        """Create the LangGraph state machine."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(TRADINGVIEW_TOOLS))

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )

        # Add edge from tools back to agent
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def _agent_node(self, state: AgentState) -> Dict[str, Any]:
        """Process agent reasoning and tool selection."""
        messages = state.get("messages", [])
        portfolio = state.get("portfolio", [])

        # Add system prompt
        system_prompt = f"""You are a PSX (Pakistan Stock Exchange) portfolio analysis assistant.

Current portfolio:
{self._format_portfolio(portfolio)}

Your capabilities:
- Analyze PSX stocks using technical indicators
- Find top gainers/losers
- Identify oversold/overbought opportunities
- Provide investment insights
- Calculate portfolio performance

Be concise and actionable in your responses. Always use tools to get real-time data."""

        full_messages = [SystemMessage(content=system_prompt)] + messages

        # Call LLM with tools
        response = self.llm_with_tools.invoke(full_messages)

        return {"messages": [response]}

    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue to tools or end."""
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None

        # Check if there are tool calls
        if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "continue"

        return "end"

    def _format_portfolio(self, portfolio: List[Dict[str, Any]]) -> str:
        """Format portfolio for display."""
        if not portfolio:
            return "No stocks in portfolio"

        lines = []
        for item in portfolio:
            lines.append(
                f"- {item['symbol']}: {item['quantity']} shares @ {item['buy_price']} PKR"
            )
        return "\n".join(lines)

    def query(self, user_query: str, portfolio: List[Dict[str, Any]] = None) -> str:
        """
        Process a user query with optional portfolio context.

        Args:
            user_query: Natural language query from user
            portfolio: Optional list of portfolio items

        Returns:
            AI response as string
        """
        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "user_query": user_query,
            "portfolio": portfolio or [],
            "analysis_result": {},
            "next_action": ""
        }

        # Run the graph
        result = self.graph.invoke(initial_state)

        # Extract final response
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'content'):
                return last_message.content

        return "I couldn't process that request."

    def analyze_portfolio(self, portfolio: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a user's portfolio and provide insights.

        Args:
            portfolio: List of stocks with symbol, quantity, buy_price

        Returns:
            Analysis with current values, P&L, and recommendations
        """
        query = f"""Analyze my portfolio and provide:
1. Current value of each stock
2. Profit/loss for each position
3. Overall portfolio performance
4. Recommendations (hold/buy more/sell)

Calculate using current market prices."""

        response = self.query(query, portfolio)

        return {
            "analysis": response,
            "portfolio": portfolio,
            "timestamp": "now"  # In production, use actual timestamp
        }


# Singleton instance
_agent_instance = None


def get_agent() -> PortfolioAgent:
    """Get or create the agent singleton."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = PortfolioAgent()
    return _agent_instance
