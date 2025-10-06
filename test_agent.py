"""Test script for the portfolio agent."""

import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

from agents.portfolio_agent import PortfolioAgent
from services.email_service import EmailService

def test_basic_query():
    """Test basic agent query."""
    print("\n" + "="*60)
    print("TEST 1: Basic Query - Top PSX Gainers")
    print("="*60)

    agent = PortfolioAgent()
    response = agent.query("What are the top 5 PSX gainers today?")

    print(f"\nResponse:\n{response}\n")


def test_portfolio_analysis():
    """Test portfolio analysis."""
    print("\n" + "="*60)
    print("TEST 2: Portfolio Analysis")
    print("="*60)

    # Sample portfolio
    portfolio = [
        {"symbol": "PSX:SHEZ", "quantity": 100, "buy_price": 280.0},
        {"symbol": "PSX:OGDC", "quantity": 200, "buy_price": 150.0},
    ]

    agent = PortfolioAgent()
    result = agent.analyze_portfolio(portfolio)

    print(f"\nAnalysis:\n{result['analysis']}\n")


def test_specific_stock():
    """Test specific stock analysis."""
    print("\n" + "="*60)
    print("TEST 3: Specific Stock Analysis")
    print("="*60)

    agent = PortfolioAgent()
    response = agent.query("Give me a detailed analysis of SHEZ stock")

    print(f"\nResponse:\n{response}\n")


def test_email_service():
    """Test email service."""
    print("\n" + "="*60)
    print("TEST 4: Email Service (Mock)")
    print("="*60)

    email_service = EmailService()

    portfolio_analysis = {
        "analysis": "Your portfolio is performing well with a 5% gain overall.",
        "portfolio": [
            {"symbol": "PSX:SHEZ", "quantity": 100, "buy_price": 280.0}
        ]
    }

    alerts = [
        {"symbol": "PSX:SHEZ", "message": "Price target of 290 PKR reached"}
    ]

    email_service.send_portfolio_update(
        to_email="test@example.com",
        portfolio_analysis=portfolio_analysis,
        alerts=alerts
    )


def main():
    """Run all tests."""
    print("""
    ╔═══════════════════════════════════════╗
    ║  PSX Portfolio Agent Test Suite       ║
    ╚═══════════════════════════════════════╝
    """)

    try:
        test_basic_query()
        test_portfolio_analysis()
        test_specific_stock()
        test_email_service()

        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
