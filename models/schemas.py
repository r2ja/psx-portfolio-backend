"""Pydantic models for API requests/responses."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class PortfolioItem(BaseModel):
    """A single stock in user's portfolio."""
    symbol: str = Field(..., description="Stock symbol (e.g., PSX:SHEZ)")
    quantity: int = Field(..., gt=0, description="Number of shares")
    buy_price: float = Field(..., gt=0, description="Purchase price per share")


class QueryRequest(BaseModel):
    """Request for natural language query."""
    query: str = Field(..., description="User's natural language question")
    portfolio: Optional[List[PortfolioItem]] = Field(default=None, description="Optional portfolio context")


class StockData(BaseModel):
    """Stock data for display."""
    symbol: str
    price: float
    change: float
    changePercent: float
    rsi: Optional[float] = None
    recommendation: Optional[str] = None
    volume: Optional[int] = None


class QueryResponse(BaseModel):
    """Response from agent query."""
    response: str = Field(..., description="AI-generated response")
    timestamp: str
    stocks: Optional[List[StockData]] = Field(default=None, description="Extracted stock data")


class PortfolioAnalysisRequest(BaseModel):
    """Request for portfolio analysis."""
    portfolio: List[PortfolioItem]


class PortfolioAnalysisResponse(BaseModel):
    """Portfolio analysis result."""
    analysis: str
    portfolio: List[PortfolioItem]
    timestamp: str


class Alert(BaseModel):
    """Alert configuration."""
    symbol: str
    alert_type: str = Field(..., description="price_target, rsi_oversold, rsi_overbought, volume_spike")
    condition: Dict[str, Any] = Field(..., description="Alert condition parameters")
    is_active: bool = True


class EmailAlertRequest(BaseModel):
    """Request to send email alert."""
    email: str
    portfolio: List[PortfolioItem]
    alerts: Optional[List[Alert]] = None
