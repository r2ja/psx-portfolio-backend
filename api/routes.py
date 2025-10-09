"""FastAPI routes for the portfolio API."""

from fastapi import APIRouter, HTTPException
from typing import List

from models.schemas import (
    QueryRequest,
    QueryResponse,
    PortfolioAnalysisRequest,
    PortfolioAnalysisResponse,
    EmailAlertRequest
)
from agents.portfolio_agent import get_agent
from services.email_service import get_email_service
from datetime import datetime

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Ask the AI agent a natural language question about stocks or portfolio.

    Examples:
    - "What are the top PSX gainers today?"
    - "Should I buy SHEZ?"
    - "Analyze my portfolio performance"
    """
    try:
        agent = get_agent()

        # Convert portfolio items to dicts
        portfolio = None
        if request.portfolio:
            portfolio = [item.dict() for item in request.portfolio]

        # Get response from agent (now returns dict with response and stocks)
        result = agent.query(request.query, portfolio)

        return QueryResponse(
            response=result.get("response", "No response"),
            timestamp=datetime.now().isoformat(),
            stocks=result.get("stocks", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/analyze", response_model=PortfolioAnalysisResponse)
async def analyze_portfolio(request: PortfolioAnalysisRequest):
    """
    Get comprehensive analysis of user's portfolio.

    Returns:
    - Current value of each position
    - Profit/loss calculations
    - Technical analysis signals
    - Buy/sell/hold recommendations
    """
    try:
        agent = get_agent()
        portfolio = [item.dict() for item in request.portfolio]

        result = agent.analyze_portfolio(portfolio)

        return PortfolioAnalysisResponse(
            analysis=result["analysis"],
            portfolio=request.portfolio,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email/send-update")
async def send_email_update(request: EmailAlertRequest):
    """
    Send portfolio update email to user.

    This can be called:
    - Manually by user
    - By cron job for daily updates
    - When alerts are triggered
    """
    try:
        agent = get_agent()
        email_service = get_email_service()

        # Analyze portfolio
        portfolio = [item.dict() for item in request.portfolio]
        analysis = agent.analyze_portfolio(portfolio)

        # Format alerts if provided
        alerts = None
        if request.alerts:
            alerts = [alert.dict() for alert in request.alerts]

        # Send email
        success = email_service.send_portfolio_update(
            to_email=request.email,
            portfolio_analysis=analysis,
            alerts=alerts
        )

        if success:
            return {"message": "Email sent successfully", "timestamp": datetime.now().isoformat()}
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/top-gainers")
async def get_top_gainers(limit: int = 10):
    """
    Get top gaining PSX stocks.

    Query params:
    - limit: Number of results (default 10)
    """
    try:
        from tools.tradingview_tools import get_psx_top_gainers
        result = get_psx_top_gainers.invoke({"limit": limit})
        return {"gainers": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/top-losers")
async def get_top_losers(limit: int = 10):
    """
    Get top losing PSX stocks.

    Query params:
    - limit: Number of results (default 10)
    """
    try:
        from tools.tradingview_tools import get_psx_top_losers
        result = get_psx_top_losers.invoke({"limit": limit})
        return {"losers": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/{symbol}")
async def get_stock_info(symbol: str):
    """
    Get detailed analysis for a specific stock.

    Path params:
    - symbol: Stock ticker (e.g., SHEZ, OGDC) - PSX: prefix optional
    """
    try:
        from tools.tradingview_tools import get_stock_analysis
        result = get_stock_analysis.invoke({"symbol": symbol})

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stocks/current-prices")
async def get_current_prices(symbols: List[str]):
    """
    Get current prices for multiple stocks.

    Request body: ["SHEZ", "OGDC", "PSO"]
    Returns: {"SHEZ": 45.50, "OGDC": 120.30, ...}
    """
    try:
        from tools.tradingview_tools import get_stock_analysis
        prices = {}

        for symbol in symbols:
            result = get_stock_analysis.invoke({"symbol": symbol})
            if "error" not in result:
                prices[symbol] = result["price_data"]["current_price"]

        return prices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
