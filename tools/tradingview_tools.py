"""TradingView MCP integration as LangChain tools."""

from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from tradingview_screener import Query
from tradingview_screener.column import Column


@tool
def get_psx_top_gainers(limit: int = 10, timeframe: str = "1D") -> List[Dict[str, Any]]:
    """
    Get top gaining PSX stocks.

    Args:
        limit: Number of stocks to return (default 10)
        timeframe: Time period - 5m, 15m, 1h, 4h, 1D, 1W, 1M (default 1D)

    Returns:
        List of stocks with symbol, price, change %, and volume
    """
    try:
        q = Query().set_markets('pakistan').select('close', 'volume', 'change', 'open').limit(limit)
        total, df = q.get_scanner_data()

        if df is None or df.empty:
            return []

        # Sort by change percentage descending
        df_sorted = df.sort_values('change', ascending=False)

        results = []
        for _, row in df_sorted.head(limit).iterrows():
            results.append({
                "symbol": row['ticker'],
                "price": float(row['close']),
                "change_percent": float(row['change']),
                "volume": int(row['volume']),
                "open": float(row['open'])
            })

        return results
    except Exception as e:
        return [{"error": str(e)}]


@tool
def get_psx_top_losers(limit: int = 10, timeframe: str = "1D") -> List[Dict[str, Any]]:
    """
    Get top losing PSX stocks.

    Args:
        limit: Number of stocks to return (default 10)
        timeframe: Time period (default 1D)

    Returns:
        List of stocks with symbol, price, change %, and volume
    """
    try:
        q = Query().set_markets('pakistan').select('close', 'volume', 'change', 'open').limit(limit * 2)
        total, df = q.get_scanner_data()

        if df is None or df.empty:
            return []

        # Sort by change percentage ascending (most negative first)
        df_sorted = df.sort_values('change', ascending=True)

        results = []
        for _, row in df_sorted.head(limit).iterrows():
            results.append({
                "symbol": row['ticker'],
                "price": float(row['close']),
                "change_percent": float(row['change']),
                "volume": int(row['volume']),
                "open": float(row['open'])
            })

        return results
    except Exception as e:
        return [{"error": str(e)}]


@tool
def get_stock_analysis(symbol: str) -> Dict[str, Any]:
    """
    Get detailed technical analysis for a specific PSX stock.

    Args:
        symbol: Stock symbol (e.g., "SHEZ", "OGDC") - PSX: prefix optional

    Returns:
        Detailed analysis with price, indicators, and signals
    """
    try:
        # Ensure PSX prefix
        if not symbol.startswith("PSX:"):
            symbol = f"PSX:{symbol.upper()}"

        q = Query().set_markets('pakistan').set_tickers(symbol).select(
            'close', 'open', 'high', 'low', 'volume',
            'RSI', 'SMA20', 'EMA50', 'BB.upper', 'BB.lower', 'MACD.macd', 'MACD.signal'
        )
        total, df = q.get_scanner_data()

        if df is None or df.empty:
            return {"error": f"No data found for {symbol}"}

        row = df.iloc[0]

        # Calculate metrics
        close = float(row['close'])
        open_price = float(row['open'])
        change_pct = ((close - open_price) / open_price) * 100 if open_price else 0

        rsi = float(row.get('RSI', 0))
        bb_upper = float(row.get('BB.upper', 0))
        bb_lower = float(row.get('BB.lower', 0))

        # Determine signals
        rsi_signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
        bb_signal = "Above Upper Band" if close > bb_upper else "Below Lower Band" if close < bb_lower else "Within Bands"

        return {
            "symbol": symbol,
            "price_data": {
                "current_price": close,
                "open": open_price,
                "high": float(row['high']),
                "low": float(row['low']),
                "change_percent": round(change_pct, 2),
                "volume": int(row['volume'])
            },
            "technical_indicators": {
                "rsi": round(rsi, 2),
                "rsi_signal": rsi_signal,
                "sma20": float(row.get('SMA20', 0)),
                "ema50": float(row.get('EMA50', 0)),
                "bb_upper": bb_upper,
                "bb_lower": bb_lower,
                "bb_signal": bb_signal,
                "macd": float(row.get('MACD.macd', 0)),
                "macd_signal": float(row.get('MACD.signal', 0))
            },
            "overall_signal": "Bullish" if change_pct > 2 and rsi < 70 else "Bearish" if change_pct < -2 else "Neutral"
        }
    except Exception as e:
        return {"error": str(e)}


@tool
def scan_oversold_stocks(rsi_threshold: float = 30, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Find oversold PSX stocks (potential buying opportunities).

    Args:
        rsi_threshold: RSI value below which stock is considered oversold (default 30)
        limit: Number of results (default 10)

    Returns:
        List of oversold stocks with RSI and price data
    """
    try:
        q = Query().set_markets('pakistan').select(
            'close', 'volume', 'change', 'RSI'
        ).limit(100)  # Get more to filter

        total, df = q.get_scanner_data()

        if df is None or df.empty:
            return []

        # Filter by RSI
        df_filtered = df[df['RSI'] < rsi_threshold].copy()
        df_filtered = df_filtered.sort_values('RSI', ascending=True)

        results = []
        for _, row in df_filtered.head(limit).iterrows():
            results.append({
                "symbol": row['ticker'],
                "price": float(row['close']),
                "change_percent": float(row['change']),
                "rsi": round(float(row['RSI']), 2),
                "volume": int(row['volume']),
                "signal": "Oversold - Potential Buy"
            })

        return results
    except Exception as e:
        return [{"error": str(e)}]


@tool
def scan_overbought_stocks(rsi_threshold: float = 70, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Find overbought PSX stocks (potential selling opportunities).

    Args:
        rsi_threshold: RSI value above which stock is considered overbought (default 70)
        limit: Number of results (default 10)

    Returns:
        List of overbought stocks with RSI and price data
    """
    try:
        q = Query().set_markets('pakistan').select(
            'close', 'volume', 'change', 'RSI'
        ).limit(100)

        total, df = q.get_scanner_data()

        if df is None or df.empty:
            return []

        # Filter by RSI
        df_filtered = df[df['RSI'] > rsi_threshold].copy()
        df_filtered = df_filtered.sort_values('RSI', ascending=False)

        results = []
        for _, row in df_filtered.head(limit).iterrows():
            results.append({
                "symbol": row['ticker'],
                "price": float(row['close']),
                "change_percent": float(row['change']),
                "rsi": round(float(row['RSI']), 2),
                "volume": int(row['volume']),
                "signal": "Overbought - Potential Sell"
            })

        return results
    except Exception as e:
        return [{"error": str(e)}]


# Export all tools
TRADINGVIEW_TOOLS = [
    get_psx_top_gainers,
    get_psx_top_losers,
    get_stock_analysis,
    scan_oversold_stocks,
    scan_overbought_stocks
]
