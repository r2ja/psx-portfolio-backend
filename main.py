"""Main FastAPI application entry point."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.routes import router

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="PSX Portfolio API",
    description="AI-powered PSX stock portfolio management with email alerts",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PSX Portfolio API",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn

    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))

    print(f"""
    ╔═══════════════════════════════════════╗
    ║  PSX Portfolio Backend API            ║
    ║  Powered by LangGraph + Claude        ║
    ╚═══════════════════════════════════════╝

    🚀 Server starting on http://localhost:{port}
    📚 API Docs: http://localhost:{port}/docs
    🔥 Interactive Docs: http://localhost:{port}/redoc
    """)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
