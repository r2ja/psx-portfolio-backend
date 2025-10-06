## PSX Portfolio Backend - Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API key
# ANTHROPIC_API_KEY=your_key_here
```

### 3. Test the Agent

```bash
python test_agent.py
```

This will run 4 tests:
- ✅ Top PSX gainers query
- ✅ Portfolio analysis
- ✅ Specific stock analysis
- ✅ Email service (mock)

### 4. Run the API Server

```bash
python main.py
```

Server will start on http://localhost:8000

### 5. Try the API

**Interactive Docs:** http://localhost:8000/docs

**Example Requests:**

```bash
# Ask a question
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the top 5 PSX gainers?",
    "portfolio": null
  }'

# Analyze portfolio
curl -X POST http://localhost:8000/api/v1/portfolio/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio": [
      {"symbol": "PSX:SHEZ", "quantity": 100, "buy_price": 280},
      {"symbol": "PSX:OGDC", "quantity": 200, "buy_price": 150}
    ]
  }'

# Get top gainers
curl http://localhost:8000/api/v1/stocks/top-gainers?limit=5

# Get specific stock
curl http://localhost:8000/api/v1/stocks/SHEZ
```

---

## API Endpoints

### Query Agent
**POST** `/api/v1/query`
- Natural language queries
- Optional portfolio context

### Portfolio Analysis
**POST** `/api/v1/portfolio/analyze`
- Comprehensive portfolio analysis
- P&L calculations
- Recommendations

### Email Alerts
**POST** `/api/v1/email/send-update`
- Send portfolio update email
- Include alerts if triggered

### Market Data
**GET** `/api/v1/stocks/top-gainers`
**GET** `/api/v1/stocks/top-losers`
**GET** `/api/v1/stocks/{symbol}`

---

## Architecture

```
┌─────────────┐
│   FastAPI   │  ← REST API endpoints
└──────┬──────┘
       │
┌──────▼──────┐
│  LangGraph  │  ← Agent orchestration
│   Agent     │
└──────┬──────┘
       │
   ┌───┴────┐
   │        │
┌──▼──┐  ┌─▼─────────┐
│Tools│  │  Claude    │
│     │  │  Sonnet 4  │
└─────┘  └────────────┘
   │
   └─► TradingView API (via tradingview-screener)
```

---

## Next Steps

1. **Add Supabase integration** for persistent storage
2. **Integrate Resend** for real email sending
3. **Add cron jobs** for daily updates
4. **Build frontend** (Next.js)

---

## Features

✅ Natural language queries about PSX stocks
✅ Portfolio P&L analysis
✅ Technical indicators (RSI, BB, MACD, etc.)
✅ Top gainers/losers scanning
✅ Oversold/overbought detection
✅ Email alerts (mock mode for now)
✅ RESTful API with FastAPI
✅ Interactive API docs
