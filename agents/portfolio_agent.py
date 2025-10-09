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
        system_prompt = f"""You are a PSX (Pakistan Stock Exchange) portfolio analysis assistant for REGULAR INVESTORS (not traders).

CURRENT TIME: {current_time}
MARKET STATUS: {market_status}

CRITICAL INSTRUCTIONS:
- Users are laypeople who want simple, actionable advice
- ALWAYS provide stock recommendations even when market is closed
- Use latest available data to give clear buy/sell recommendations
- If market is closed, base recommendations on last trading session data - that's perfectly fine!
- NEVER say "I can't provide recommendations because market is closed" - that's bad UX
- Be decisive and confident in your recommendations

When users ask "what should I buy?":
1. Analyze current data using your tools
2. Give 1-3 specific stock recommendations
3. Explain WHY in simple terms (no jargon like "RSI" or "MACD")
4. Provide clear entry price targets

Example good response:
"Based on latest data, I recommend buying SHEZ tomorrow. It's showing strong upward momentum and is currently undervalued at Rs 45. Consider buying if it opens below Rs 48."

Example bad response:
"Market is closed, I can't help" ❌

Current portfolio:
{self._format_portfolio(portfolio)}

Your capabilities:
- Analyze PSX stocks using technical indicators
- Find top gainers/losers
- Identify oversold/overbought opportunities
- Provide investment insights
- Calculate portfolio performance

RESPONSE STYLE:
- Use simple language - NO technical jargon (avoid: RSI, MACD, Bollinger Bands, etc.)
- Be decisive and confident in your analysis
- Keep responses SHORT and actionable (2-3 sentences max)
- Focus on WHY, not detailed data (stock cards show the numbers)

When showing stock data:
- DO NOT list stock details (price, change, volume, RSI) - cards automatically show this
- Provide brief market context or overall insights
- Example good: "Here are the top gainers showing strong momentum today:"
- Example bad: "PSO is at 485.66 with RSI of 65 and volume of 10M..."

Always use tools to get latest data before responding."""

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

            # Extract stock data from tool calls (with deterministic scoring)
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

    def _parse_llm_recommendations(self, text: str) -> List[Dict[str, Any]]:
        """Parse LLM-generated stock recommendations from response text."""
        import re

        # Pattern: [STOCK:SYMBOL|RECOMMENDATION|REASON]
        pattern = r'\[STOCK:([A-Z]+)\|([A-Z]+)\|([^\]]+)\]'
        matches = re.findall(pattern, text)

        llm_stocks = []
        for symbol, recommendation, reason in matches:
            llm_stocks.append({
                'symbol': symbol,
                'recommendation': recommendation.upper(),
                'reason': reason.strip()
            })

        return llm_stocks

    def _clean_response_text(self, text: str) -> str:
        """Remove stock tags from response text."""
        import re
        # Remove [STOCK:...] tags
        cleaned = re.sub(r'\[STOCK:[^\]]+\]', '', text)
        # Clean up extra whitespace
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned).strip()
        return cleaned

    def _merge_stock_data(self, tool_stocks: List[Dict[str, Any]], llm_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge tool data with LLM recommendations."""
        # Create lookup for LLM recommendations
        llm_lookup = {stock['symbol']: stock for stock in llm_stocks}

        # Merge
        merged = []
        for tool_stock in tool_stocks:
            symbol = tool_stock['symbol']
            if symbol in llm_lookup:
                # Override recommendation and reason with LLM's analysis
                tool_stock['recommendation'] = llm_lookup[symbol]['recommendation']
                tool_stock['reason'] = llm_lookup[symbol]['reason']
                llm_lookup.pop(symbol)  # Remove from lookup
            merged.append(tool_stock)

        # Add any LLM-recommended stocks not in tool data (with placeholder data)
        for symbol, llm_stock in llm_lookup.items():
            merged.append({
                'symbol': symbol,
                'price': 0,  # Will need to be fetched
                'change': 0,
                'changePercent': 0,
                'recommendation': llm_stock['recommendation'],
                'reason': llm_stock['reason']
            })

        return merged[:10]

    def _format_stock_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format stock data to match frontend expectations."""
        try:
            symbol = raw_data.get('symbol', '').replace('PSX:', '')

            # Handle different data formats
            if 'price_data' in raw_data:
                # Detailed stock analysis format
                price_data = raw_data['price_data']
                tech = raw_data.get('technical_indicators', {})

                stock_data = {
                    'symbol': symbol,
                    'price': price_data.get('current_price', 0),
                    'change': price_data.get('current_price', 0) - price_data.get('open', 0),
                    'changePercent': price_data.get('change_percent', 0),
                    'rsi': tech.get('rsi'),
                    'volume': price_data.get('volume'),
                    'sma20': tech.get('sma20'),
                    'ema50': tech.get('ema50'),
                }
            else:
                # Simple format from gainers/losers
                price = raw_data.get('price', raw_data.get('close', 0))
                change_pct = raw_data.get('change_percent', raw_data.get('change', 0))
                open_price = raw_data.get('open', price)
                change = price - open_price

                stock_data = {
                    'symbol': symbol,
                    'price': price,
                    'change': change,
                    'changePercent': change_pct,
                    'rsi': raw_data.get('rsi'),
                    'volume': raw_data.get('volume'),
                }

            # Apply deterministic scoring system
            recommendation, reason, score = self._calculate_recommendation(stock_data)
            stock_data['recommendation'] = recommendation
            stock_data['reason'] = reason

            return stock_data
        except Exception as e:
            print(f"Error formatting stock data: {e}")
            return None

    def _calculate_recommendation(self, stock_data: Dict[str, Any]) -> tuple[str, str, int]:
        """
        Deterministic scoring system for stock recommendations.
        Returns: (recommendation, reason, score)
        """
        score = 0
        reasons = []

        rsi = stock_data.get('rsi')
        change_pct = stock_data.get('changePercent', 0)
        price = stock_data.get('price', 0)
        sma20 = stock_data.get('sma20')
        ema50 = stock_data.get('ema50')

        # RSI Analysis (strong signal)
        if rsi is not None:
            if rsi < 30:
                score += 3
                reasons.append("oversold")
            elif rsi < 40:
                score += 1
                reasons.append("undervalued")
            elif rsi > 70:
                score -= 3
                reasons.append("overbought")
            elif rsi > 60:
                score -= 1
                reasons.append("overvalued")

        # Price change analysis
        if change_pct > 5:
            score -= 2
            reasons.append("strong rally")
        elif change_pct > 2:
            score += 1
            reasons.append("positive momentum")
        elif change_pct < -5:
            score += 2
            reasons.append("big dip")
        elif change_pct < -2:
            score += 1
            reasons.append("slight pullback")

        # Moving average analysis (trend)
        if sma20 and ema50 and price:
            if price > sma20 and sma20 > ema50:
                score += 2
                reasons.append("strong uptrend")
            elif price < sma20 and sma20 < ema50:
                score -= 2
                reasons.append("downtrend")

        # Determine recommendation from score
        if score >= 3:
            recommendation = "BUY"
            reason = "Good opportunity - " + ", ".join(reasons[:2]) if reasons else "Good value"
        elif score <= -3:
            recommendation = "SELL"
            reason = "Take profits - " + ", ".join(reasons[:2]) if reasons else "Overpriced"
        else:
            recommendation = "HOLD"
            if reasons:
                reason = "Mixed signals - " + ", ".join(reasons[:2])
            else:
                reason = "Stable, wait and see"

        return recommendation, reason, score

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
