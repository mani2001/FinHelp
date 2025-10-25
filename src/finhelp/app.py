# src/finhelp/app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .mcp_client import mcp_session
from .finance_chat import finance_chat
from .agent import run_earnings_analysis

app = FastAPI(title="Finance AI Assistant")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check - verify Tavily MCP connection."""
    try:
        async with mcp_session() as session:
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
        return {"status": "ok", "tools": names}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post("/api/finance-chat")
async def finance_chat_endpoint(request: dict):
    """
    Finance chat with guardrails and web search.
    
    Request body:
    {
        "message": "What is Apple's current stock price?",
        "conversation": []
    }
    """
    try:
        message = request.get("message", "")
        conversation = request.get("conversation", [])
        
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        
        result = await finance_chat(message, conversation)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/earnings-analyze")
async def earnings_analyze_endpoint(request: dict):
    """
    Analyze earnings call using LangGraph workflow.
    
    Request body:
    {
        "ticker": "AAPL",
        "quarter": "Q3",
        "year": "2024"
    }
    """
    try:
        ticker = request.get("ticker", "").upper()
        quarter = request.get("quarter", "").upper()
        year = request.get("year", "")
        
        if not ticker or not quarter or not year:
            raise HTTPException(status_code=400, detail="ticker, quarter, and year are required")
        
        if quarter not in ["Q1", "Q2", "Q3", "Q4"]:
            raise HTTPException(status_code=400, detail="quarter must be Q1, Q2, Q3, or Q4")
        
        result = await run_earnings_analysis(ticker, quarter, year)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))