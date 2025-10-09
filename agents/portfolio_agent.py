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

        # Get current time in Pakistan timezone
        from datetime import datetime
        import pytz

        pk_tz = pytz.timezone('Asia/Karachi')
        now = datetime.now(pk_tz)
        current_time = now.strftime("%A, %B %d, %Y at %I:%M %p PKT")

        # Determine market status (PSX trading hours: 9:15 AM - 3:30 PM, Mon-Fri)
        is_weekend = now.weekday() >= 5  # Saturday = 5, Sunday = 6
        market_open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
        is_market_hours = market_open_time <= now <= market_close_time

        if is_weekend:
            market_status = "CLOSED (Weekend)"
        elif is_market_hours:
            market_status = "OPEN"
        else:
            market_status = "CLOSED"

        # Add system prompt
        system_prompt = f"""You are a PSX (Pakistan Stock Exchange) portfolio analysis assistant.

CURRENT TIME: {current_time}
MARKET STATUS: {market_status}

IMPORTANT: The PSX market operates Monday-Friday, 9:15 AM - 3:30 PM PKT.
- If market is CLOSED, remind users that data shown is from the last trading session
- If outside trading hours, mention that live trading is not currently active
- Always consider the current time when giving advice about immediate actions

Current portfolio:
{self._format_portfolio(portfolio)}

Your capabilities:
- Analyze PSX stocks using technical indicators
- Find top gainers/losers
- Identify oversold/overbought opportunities
- Provide investment insights
- Calculate portfolio performance

IMPORTANT: When showing stock data, DO NOT list stock details in your text response (like price, change, volume, etc.).
The stock cards will automatically display this information visually.
Instead, provide brief context, insights, or recommendations about the stocks shown.

Example:
Good: "Here are today's top PSX gainers showing strong momentum:"
Bad: "Top gainers: SHEZ at 45.2 (+5.3%), OGDC at 120.5 (+3.2%)..."

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

    def query(self, user_query: str, portfolio: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user query with optional portfolio context.

        Args:
            user_query: Natural language query from user
            portfolio: Optional list of portfolio items

        Returns:
            Dict with response text and extracted stock data
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

        # Extract final response and tool calls
        messages = result.get("messages", [])
        response_text = "I couldn't process that request."
        stocks = []

        if messages:
            # Extract the final AI message
            for msg in reversed(messages):
                if hasattr(msg, 'content') and isinstance(msg.content, str) and msg.content.strip():
                    response_text = msg.content
                    break

            # Extract stock data from tool calls
            stocks = self._extract_stocks_from_messages(messages)

        return {
            "response": response_text,
            "stocks": stocks
        }

    def _extract_stocks_from_messages(self, messages: List) -> List[Dict[str, Any]]:
        """Extract stock data from tool call results in messages."""
        stocks = []
        seen_symbols = set()

        for msg in messages:
            # Check for tool messages
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                try:
                    import json
                    # Try to parse if it's JSON
                    if msg.content.strip().startswith('[') or msg.content.strip().startswith('{'):
                        data = json.loads(msg.content)

                        # Handle list of stocks
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and 'symbol' in item:
                                    stock = self._format_stock_data(item)
                                    if stock and stock['symbol'] not in seen_symbols:
                                        stocks.append(stock)
                                        seen_symbols.add(stock['symbol'])

                        # Handle single stock
                        elif isinstance(data, dict) and 'symbol' in data:
                            stock = self._format_stock_data(data)
                            if stock and stock['symbol'] not in seen_symbols:
                                stocks.append(stock)
                                seen_symbols.add(stock['symbol'])
                except:
                    pass

        return stocks[:10]  # Limit to 10 stocks

    def _format_stock_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format stock data to match frontend expectations."""
        try:
            symbol = raw_data.get('symbol', '').replace('PSX:', '')

            # Handle different data formats
            if 'price_data' in raw_data:
                # Detailed stock analysis format
                price_data = raw_data['price_data']
                tech = raw_data.get('technical_indicators', {})
                return {
                    'symbol': symbol,
                    'price': price_data.get('current_price', 0),
                    'change': price_data.get('current_price', 0) - price_data.get('open', 0),
                    'changePercent': price_data.get('change_percent', 0),
                    'rsi': tech.get('rsi'),
                    'volume': price_data.get('volume'),
                    'recommendation': self._get_recommendation(tech.get('rsi'), price_data.get('change_percent', 0))
                }
            else:
                # Simple format from gainers/losers
                price = raw_data.get('price', raw_data.get('close', 0))
                change_pct = raw_data.get('change_percent', raw_data.get('change', 0))
                open_price = raw_data.get('open', price)
                change = price - open_price

                return {
                    'symbol': symbol,
                    'price': price,
                    'change': change,
                    'changePercent': change_pct,
                    'rsi': raw_data.get('rsi'),
                    'volume': raw_data.get('volume'),
                    'recommendation': self._get_recommendation(raw_data.get('rsi'), change_pct)
                }
        except Exception as e:
            print(f"Error formatting stock data: {e}")
            return None

    def _get_recommendation(self, rsi: float = None, change_pct: float = 0) -> str:
        """Determine buy/sell/hold recommendation."""
        if rsi is not None:
            if rsi < 30:
                return "BUY"
            elif rsi > 70:
                return "SELL"

        if change_pct > 5:
            return "SELL"
        elif change_pct < -5:
            return "BUY"

        return "HOLD"

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
