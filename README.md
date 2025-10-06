# PSX Portfolio Backend

Agentic backend for PSX stock portfolio management with AI-powered analysis and alerts.

## Architecture

- **LangGraph**: Multi-agent orchestration
- **MCP Integration**: TradingView data access
- **FastAPI**: REST API endpoints
- **Anthropic Claude**: AI analysis and insights

## Features

- Portfolio management
- Real-time stock analysis
- AI-powered insights
- Email alerts
- Natural language queries

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY

# Run server
python main.py
```

## Project Structure

```
psx-portfolio-backend/
├── agents/           # LangGraph agents
├── tools/            # MCP and custom tools
├── services/         # Business logic
├── api/              # FastAPI routes
├── models/           # Pydantic models
└── main.py          # Entry point
```
